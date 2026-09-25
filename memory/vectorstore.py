import os
import re
import shutil
import textract
import hashlib
from functools import lru_cache
from langchain_text_splitters import TokenTextSplitter
from langchain_core.documents import Document
from langchain_core.tools import tool
from config.settings import CHROMA_PERSIST_DIR, LOCAL_EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_CONTEXT, EMBEDDING_MODEL_CHUNK
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

@lru_cache(maxsize=1)
def get_embeddings():
    return OpenAIEmbeddings(
        model=LOCAL_EMBEDDING_MODEL_NAME,
        openai_api_base="http://localhost:1234/v1",
        openai_api_key="lm-studio",
        check_embedding_ctx_length=False,
    )


def get_store():
    return Chroma(
        collection_name="NL2SQL",
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_PERSIST_DIR,
    )


def get_retriever():
    return get_store().as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5},
    )


@lru_cache(maxsize=1)
def get_text_splitter():
    return TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=EMBEDDING_MODEL_CONTEXT,
        chunk_overlap=EMBEDDING_MODEL_CHUNK,
    )
INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_NAMES = {"", ".", "..", "chroma.sqlite3"}

def sanitize_name(original: str) -> str:
    name = os.path.basename(original).strip()
    name = INVALID_NAME_CHARS.sub("_", name).strip(" .")
    if name.lower() in RESERVED_NAMES:
        raise ValueError(f"reserved file name: {original}")
    if not name:
        raise ValueError("empty file name")
    return name


def _sha1_of(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_data(file_path: str) -> list[Document]:
    try:
        text = textract.process(file_path).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to parse the file: {e}")
    return [
        Document(
            page_content=text,
            metadata={
                "source": os.path.basename(file_path),
                "sha1": _sha1_of(file_path),
            },
        )
    ]


def save_data(file_name: str, batch_size: int = 50):
    full_path = os.path.join(CHROMA_PERSIST_DIR, file_name)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    source = os.path.basename(full_path)
    get_store().delete(where={"source": source})
    docs = read_data(full_path)
    splits = get_text_splitter().split_documents(docs)
    get_store().add_documents(documents=splits, batch_size=batch_size)

def ingest_file(upload_path: str, original_name: str) -> str:
    if not os.path.isfile(upload_path):
        raise ValueError(f"uploaded file not found: {upload_path}")
    source = sanitize_name(original_name)
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    dest = os.path.join(CHROMA_PERSIST_DIR, source)
    digest = _sha1_of(upload_path)
    if os.path.abspath(upload_path) != os.path.abspath(dest):
        shutil.copyfile(upload_path, dest)
    try:
        existing = get_store()._collection.get(
            where={"source": source}, include=["metadatas"], limit=1
        )
        existing_sha1 = (existing.get("metadatas") or [{}])[0].get("sha1")
    except Exception:
        existing_sha1 = None
    if existing_sha1 == digest:
        return "already-indexed"
    try:
        save_data(source)
    except Exception:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise
    return "indexed"

def list_data() -> list[str]:
    collection = get_store()._collection
    results = collection.get(include=["metadatas"])
    sources = set()
    for meta in results.get("metadatas", []) or []:
        if meta and "source" in meta:
            sources.add(meta["source"])
    return sorted(sources)


def delete_data(file_name: str) -> str:
    source = os.path.basename(file_name)
    get_store().delete(where={"source": source})
    try:
        os.remove(os.path.join(CHROMA_PERSIST_DIR, source))
    except OSError:
        pass
    return f"Deleted documents with source: {source}"
