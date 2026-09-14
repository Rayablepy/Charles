import os
import textract
from functools import lru_cache
from langchain_text_splitters import TokenTextSplitter
from langchain_core.documents import Document
from langchain_core.tools import tool
from config.settings import CHROMA_PERSIST_DIR, LOCAL_EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_CONTEXT, EMBEDDING_MODEL_CHUNK
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


@lru_cache(maxsize=1)
def _get_embeddings():
    return OpenAIEmbeddings(
        model=LOCAL_EMBEDDING_MODEL_NAME,
        openai_api_base="http://localhost:1234/v1",
        openai_api_key="lm-studio",
        check_embedding_ctx_length=False,
    )


@lru_cache(maxsize=1)
def _get_store():
    return Chroma(
        collection_name="NL2SQL",
        embedding_function=_get_embeddings(),
        persist_directory=CHROMA_PERSIST_DIR,
    )


@lru_cache(maxsize=1)
def _get_retriever():
    return _get_store().as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5},
    )


@lru_cache(maxsize=1)
def _get_text_splitter():
    return TokenTextSplitter(
        encoding_name="cl100k_base",
        chunk_size=EMBEDDING_MODEL_CONTEXT,
        chunk_overlap=EMBEDDING_MODEL_CHUNK,
    )


def read_data(file_path: str) -> list[Document]:
    try:
        text = textract.process(file_path).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to read {file_path}: {e}")
    return [
        Document(
            page_content=text,
            metadata={"source": os.path.basename(file_path)},
        )
    ]


def save_data(file_name: str, batch_size: int = 50):
    full_path = os.path.join(CHROMA_PERSIST_DIR, file_name)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {full_path}")
    source = os.path.basename(full_path)
    _get_store().delete(where={"source": source})
    docs = read_data(full_path)
    splits = _get_text_splitter().split_documents(docs)
    _get_store().add_documents(documents=splits, batch_size=batch_size)


def list_data() -> list[str]:
    collection = _get_store()._collection
    results = collection.get(include=["metadatas"])
    sources = set()
    for meta in results.get("metadatas", []) or []:
        if meta and "source" in meta:
            sources.add(meta["source"])
    return sorted(sources)


def delete_data(file_name: str) -> str:
    source = os.path.basename(file_name)
    _get_store().delete(where={"source": source})
    return f"Deleted documents with source: {source}"
