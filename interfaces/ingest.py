
import json
import os
import queue
import re
import sys
import tempfile
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from config.settings import (
    build_provider_model,
    find_provider_config,
    find_subagent_config,
    read_provider_configs,
    read_subagent_configs,
    write_subagent_configs,
)
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yaml

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
SKILL_FILE_NAME = "SKILL.md"
SKILL_NAME_MAX = 64
SKILL_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
PROVIDER_CONFIG_PATH = PROJECT_ROOT / "provider.json"

#pydantic outputs for fastapi endpoints
class ProviderConfig(BaseModel):
    provider: str
    model: str
    api_key: str = ""

class ProviderSelection(BaseModel):
    provider: str

class SubagentConfig(BaseModel):
    subagent:str
    enabled:bool=True
    model:str

JOBS: dict[str, dict] = {}
QUEUE: queue.Queue[str] = queue.Queue()
MAX_JOBS = 200

#all helper functions
def remember(job_id: str, job: dict) -> None:
    JOBS[job_id] = job
    while len(JOBS) > MAX_JOBS:
        JOBS.pop(next(iter(JOBS)))

def write_provider_configs(configs: list[dict]) -> None:
    PROVIDER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROVIDER_CONFIG_PATH.write_text(json.dumps(configs), encoding="utf-8")
    os.chmod(PROVIDER_CONFIG_PATH, 0o600)

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
@app.post("/subagents", status_code=HTTPStatus.OK)
async def config_subagents(subagent:SubagentConfig)->dict:
    name = subagent.subagent.strip()
    enabled = subagent.enabled
    if not name:
        raise HTTPException(status_code=400, detail="subagent is required")
    configs = read_subagent_configs()
    config = find_subagent_config(configs, name)
    if config is None:
        config = {"subagent": name}
        configs.append(config)
    config["enabled"] = enabled
    write_subagent_configs(configs)
    return {"ok": True, "subagent": name, "enabled": enabled}

@app.get("/subagents")
async def list_subagents() -> dict:
    return {
        "subagents": [
            {
                "subagent": str(config.get("subagent") or "").strip(),
                "enabled": config.get("enabled") is True,
            }
            for config in read_subagent_configs()
        ]
    }

@app.post("/provider", status_code=HTTPStatus.OK)
async def set_provider(config: ProviderConfig) -> dict:
    provider = config.provider.strip()
    model = config.model.strip()
    api_key = config.api_key.strip()
    if not provider or not model:
        raise HTTPException(status_code=400, detail="provider and model are required")
    configs = read_provider_configs()
    entry = find_provider_config(configs, provider)
    if entry is None:
        entry = {"provider": provider, "model": model, "api_key": api_key, "active": False}
        configs.append(entry)
    else:
        entry["model"] = model
        if api_key:
            entry["api_key"] = api_key
    write_provider_configs(configs)
    return {"ok": True, "provider": provider, "model": model}

@app.get("/providers")
async def list_providers() -> dict:
    return {
        "providers": [
            {
                "provider": str(config.get("provider") or "").strip(),
                "model": str(config.get("model") or "").strip(),
                "active": config.get("active") is True,
            }
            for config in read_provider_configs()
        ]
    }

@app.post("/provider/use")
async def use_provider(selection: ProviderSelection) -> dict:
    provider = selection.provider.strip()
    configs = read_provider_configs()
    if find_provider_config(configs, provider) is None:
        raise HTTPException(status_code=404, detail="provider is not configured")
    for config in configs:
        config["active"] = str(config.get("provider") or "").strip() == provider
    write_provider_configs(configs)
    return {"ok": True, "provider": provider}

@app.delete("/provider/{provider}")
async def delete_provider(provider: str) -> dict:
    configs = read_provider_configs()
    entry = find_provider_config(configs, provider)
    if entry is None:
        raise HTTPException(status_code=404, detail="provider is not configured")
    write_provider_configs([config for config in configs if config is not entry])
    return {"ok": True}

@app.post("/provider/verify")
async def check_provider():
    if build_provider_model() is None:
        return {"verified":False}
    return {"verified":True}

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

#handle skill files
def validate_skill_name(name: str) -> str:
    if len(name) > SKILL_NAME_MAX:
        raise HTTPException(status_code=400, detail="skill name exceeds 64 characters")
    if name.startswith("-") or name.endswith("-") or "--" in name:
        raise HTTPException(status_code=400, detail="skill name must use single hyphens")
    valid_chars = all(
        char == "-" or (char.isalpha() and char.islower()) or char.isdigit()
        for char in name
    )
    if not valid_chars:
        raise HTTPException(status_code=400, detail="skill name must be lowercase alphanumeric with hyphens")
    return name


def parse_skill_name(content: bytes) -> str:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="SKILL.md must be UTF-8") from exc
    match = SKILL_FRONTMATTER.match(text)
    if match is None:
        raise HTTPException(status_code=400, detail="SKILL.md needs YAML frontmatter")
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail="SKILL.md has invalid YAML") from exc
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="SKILL.md frontmatter must be a mapping")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=400, detail="skill name is required")
    if not isinstance(description, str) or not description.strip():
        raise HTTPException(status_code=400, detail="skill description is required")
    return validate_skill_name(name.strip())

def validate_file_name(name: str) -> str:
    clean = (name or "").strip()
    if not clean or clean in {".", ".."}:
        raise HTTPException(status_code=400, detail="invalid file name")
    if any(char in '<>:"/\\|?*' or ord(char) < 32 for char in clean):
        raise HTTPException(status_code=400, detail="file name has invalid characters")
    if clean.rstrip(". ") != clean:
        raise HTTPException(status_code=400, detail="file name cannot end with a dot or space")
    return clean

#handle uploaded files
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


@app.post("/skills/upload", status_code=HTTPStatus.CREATED)
async def upload_skill(file: UploadFile | None = File(default=None)) -> dict:
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="missing file")
    source = os.path.basename(file.filename.replace("\\", "/"))
    if source.lower() != SKILL_FILE_NAME.lower():
        raise HTTPException(status_code=400, detail=f"file must be named {SKILL_FILE_NAME}")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="empty file")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail=f"skill file exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
        )
    name = parse_skill_name(content)
    root = scope_dir("skills")
    target = resolve_scope_path("skills", f"locked/{name}/{SKILL_FILE_NAME}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="failed to store skill") from exc
    return {"ok": True, "name": name, "path": target.relative_to(root).as_posix()}


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
