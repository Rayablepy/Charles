
import os
import queue
import sys
import tempfile
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import PROJECT_ROOT
from memory.vectorstore import ingest_file, read_data, sanitize_name

HOST = os.getenv("INGEST_API_HOST", "127.0.0.1")
PORT = int(os.getenv("INGEST_API_PORT", "2030"))
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
TRANSCRIBE_MAX_CHARS = 100_000
STAGING_PREFIX = "rag-upload-"
TERMINAL = {"indexed", "already-indexed", "failed"}
FILE_MAX_BYTES = 512 * 1024
FILE_LIST_LIMIT = 5000

JOBS: dict[str, dict] = {}
QUEUE: queue.Queue[str] = queue.Queue()
MAX_JOBS = 200


def remember(job_id: str, job: dict) -> None:
    JOBS[job_id] = job
    while len(JOBS) > MAX_JOBS:
        JOBS.pop(next(iter(JOBS)))


def sanitize_error(text: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = os.path.abspath(os.path.expanduser("~"))
    return text.replace(root, "<PROJECT>").replace(home, "<HOME>")


def worker_loop() -> None:
    while True:
        job_id = QUEUE.get()
        job = JOBS.get(job_id)
        if not job:
            continue
        job["status"] = "ingesting"
        try:
            result = ingest_file(job["path"], job["name"])
            job["status"] = result if result in TERMINAL else "indexed"
        except Exception as e:
            job["status"] = "failed"
            job["error"] = sanitize_error(f"{type(e).__name__}: {e}")
        finally:
            try:
                os.remove(job["path"])
            except OSError:
                pass
            job.pop("path", None)


@asynccontextmanager
async def lifespan(_: FastAPI):
    threading.Thread(target=worker_loop, name="rag-ingest", daemon=True).start()
    yield


app = FastAPI(title="Charles doc manager", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["POST", "GET", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


async def stream_file(file: UploadFile, staging: str) -> int:
    size = 0
    with open(staging, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"{file.filename} is too large "
                        f"({size / (1024 * 1024):.1f} MB). "
                        f"Maximum file size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                    ),
                )
            out.write(chunk)
    return size


@app.post("/uploads", status_code=HTTPStatus.ACCEPTED)
async def upload(file: UploadFile | None = File(default=None)) -> dict:
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="missing file")

    try:
        source = sanitize_name(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    staging = os.path.join(tempfile.gettempdir(), f"{STAGING_PREFIX}{uuid.uuid4()}")
    try:
        size = await stream_file(file, staging)
    except HTTPException:
        os.remove(staging)
        raise
    except OSError as exc:
        os.remove(staging)
        raise HTTPException(status_code=500, detail="failed to store upload") from exc

    if size == 0:
        os.remove(staging)
        raise HTTPException(status_code=400, detail="empty file")

    job_id = str(uuid.uuid4())
    remember(
        job_id,
        {
            "job_id": job_id,
            "status": "queued",
            "source": source,
            "name": source,
            "path": staging,
        },
    )
    QUEUE.put(job_id)
    return {"ok": True, "job_id": job_id, "source": source, "status": "queued"}

@app.post("/transcribe", status_code=HTTPStatus.OK)
async def transcribe(file: UploadFile | None = File(default=None)) -> dict:
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="missing file")

    try:
        source = sanitize_name(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    staging = os.path.join(
        tempfile.gettempdir(),
        f"{STAGING_PREFIX}{uuid.uuid4()}{os.path.splitext(source)[1]}",
    )
    try:
        size = await stream_file(file, staging)
    except HTTPException:
        os.remove(staging)
        raise
    except OSError as exc:
        os.remove(staging)
        raise HTTPException(status_code=500, detail="failed to store upload") from exc

    try:
        if size == 0:
            raise HTTPException(status_code=400, detail="empty file")
        text = read_data(staging)[0].page_content
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=sanitize_error(f"{type(exc).__name__}: {exc}"),
        ) from exc
    finally:
        try:
            os.remove(staging)
        except OSError:
            pass

    if len(text) > TRANSCRIBE_MAX_CHARS:
        text = text[:TRANSCRIBE_MAX_CHARS] + "\n[...transcript truncated...]"
    return {"ok": True, "source": source, "text": text}


@app.get("/uploads/{job_id}")
async def job_status(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="unknown job")
    payload = {"job_id": job["job_id"], "status": job["status"], "source": job["source"]}
    if job.get("error"):
        payload["error"] = job["error"]
    return payload


def scope_dir(scope: str) -> Path:
    root = (PROJECT_ROOT / scope).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_scope_path(scope: str, raw: str) -> Path:
    root = scope_dir(scope)
    relative = (raw or "").replace("\\", "/").strip("/")
    candidate = (root / relative).resolve()
    if candidate != root and not candidate.is_relative_to(root):
        raise HTTPException(status_code=400, detail=f"path escapes the {scope} directory")
    return candidate


def validate_file_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean or clean in {".", ".."}:
        raise HTTPException(status_code=400, detail="invalid file name")
    if any(char in '<>:"/\\|?*' or ord(char) < 32 for char in clean):
        raise HTTPException(status_code=400, detail="file name has invalid characters")
    if clean.rstrip(". ") != clean:
        raise HTTPException(status_code=400, detail="file name cannot end with a dot or space")
    return clean


def list_scope_files(scope: str) -> dict:
    root = scope_dir(scope)
    files: list[dict] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            try:
                stat = full.stat()
            except OSError:
                continue
            files.append(
                {
                    "path": full.relative_to(root).as_posix(),
                    "name": name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "full_path": str(full),
                }
            )
            if len(files) >= FILE_LIST_LIMIT:
                truncated = True
                break
        if truncated:
            break
    files.sort(key=lambda item: item["path"].lower())
    return {"root": str(root), "truncated": truncated, "files": files}


def read_scope_file(scope: str, path: str) -> dict:
    target = resolve_scope_path(scope, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    try:
        stat = target.stat()
        with open(target, "rb") as handle:
            data = handle.read(FILE_MAX_BYTES)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="failed to read file") from exc
    binary = b"\x00" in data
    root = scope_dir(scope)
    return {
        "path": target.relative_to(root).as_posix(),
        "name": target.name,
        "size": stat.st_size,
        "binary": binary,
        "truncated": stat.st_size > len(data),
        "text": "" if binary else data.decode("utf-8", errors="replace"),
    }


def rename_scope_file(scope: str, path: str, name: str) -> dict:
    root = scope_dir(scope)
    target = resolve_scope_path(scope, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    new_name = validate_file_name(name)
    # A present extension stays fixed so parsing cannot break
    if target.suffix and Path(new_name).suffix.lower() != target.suffix.lower():
        raise HTTPException(status_code=400, detail="file extension cannot be changed")
    destination = (target.parent / new_name).resolve()
    if destination != root and not destination.is_relative_to(root):
        raise HTTPException(status_code=400, detail=f"path escapes the {scope} directory")
    if destination == target:
        return {
            "ok": True,
            "path": target.relative_to(root).as_posix(),
            "name": target.name,
        }
    if destination.exists():
        raise HTTPException(status_code=409, detail=f'"{new_name}" already exists')
    try:
        target.rename(destination)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="failed to rename file") from exc
    return {
        "ok": True,
        "path": destination.relative_to(root).as_posix(),
        "name": destination.name,
    }


def delete_scope_file(scope: str, path: str) -> dict:
    root = scope_dir(scope)
    target = resolve_scope_path(scope, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    try:
        target.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="failed to delete file") from exc
    return {"ok": True, "path": target.relative_to(root).as_posix()}


@app.get("/project/files")
async def project_files() -> dict:
    return list_scope_files("project")


@app.get("/skills/files")
async def skills_files() -> dict:
    return list_scope_files("skills")


@app.get("/project/file")
async def project_file(path: str = Query(...)) -> dict:
    return read_scope_file("project", path)


@app.get("/skills/file")
async def skills_file(path: str = Query(...)) -> dict:
    return read_scope_file("skills", path)


@app.post("/project/file/rename")
async def rename_project_file(path: str = Query(...), name: str = Query(...)) -> dict:
    return rename_scope_file("project", path, name)


@app.post("/skills/file/rename")
async def rename_skills_file(path: str = Query(...), name: str = Query(...)) -> dict:
    return rename_scope_file("skills", path, name)


@app.delete("/project/file")
async def delete_project_file(path: str = Query(...)) -> dict:
    return delete_scope_file("project", path)


@app.delete("/skills/file")
async def delete_skills_file(path: str = Query(...)) -> dict:
    return delete_scope_file("skills", path)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
