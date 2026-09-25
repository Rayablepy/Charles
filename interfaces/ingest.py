
import os
import queue
import sys
import tempfile
import threading
import uuid
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.vectorstore import ingest_file, sanitize_name

HOST = os.getenv("INGEST_API_HOST", "127.0.0.1")
PORT = int(os.getenv("INGEST_API_PORT", "2030"))
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
STAGING_PREFIX = "rag-upload-"
TERMINAL = {"indexed", "already-indexed", "failed"}

JOBS: dict[str, dict] = {}
QUEUE: queue.Queue[str] = queue.Queue()


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
    allow_methods=["POST", "GET", "OPTIONS"],
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
                    detail="file too large",
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
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "source": source,
        "name": source,
        "path": staging,
    }
    QUEUE.put(job_id)
    return {"ok": True, "job_id": job_id, "source": source, "status": "queued"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)