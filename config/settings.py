import json
import os
from dotenv import load_dotenv
from importlib import import_module
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_openrouter import ChatOpenRouter

load_dotenv()

#Model constants
CHAT_MODEL_NAME=os.getenv("CHAT_MODEL_NAME")
LOCAL_MODEL_NAME=os.getenv("LOCAL_MODEL_NAME")
LOCAL_EMBEDDING_MODEL_NAME=os.getenv("LOCAL_EMBEDDING_MODEL_NAME")
MODEL_PROVIDER = "openai"
LOCAL_MODEL_BASE_URL = "http://localhost:1234/v1"
PROVIDER_CONFIG_PATH = Path.home() / ".Charles" / "provider.json"

if LOCAL_MODEL_NAME:
    LOCAL_MODEL= init_chat_model(
        model=LOCAL_MODEL_NAME,
        model_provider=MODEL_PROVIDER,
        base_url=LOCAL_MODEL_BASE_URL,
        api_key="smth", #this can be anything
    )
else:
    LOCAL_MODEL= None

# provider id to model harness
PROVIDER_HARNESSES = {
    "azure-openai": "azure_openai",
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google_genai",
    "ollama": "ollama",
    "groq": "groq",
    "litellm": "litellm",
    "mistral": "mistralai",
    "openrouter": "openrouter",
    "xai": "xai",
    "deepseek": "deepseek",
    "nvidia": "nvidia",
    "together": "together",
}

# init_chat_model has no harness for these
PROVIDER_CLASSES = {
    "databricks": ("databricks_langchain", "ChatDatabricks"),
    "amazon-nova": ("langchain_amazon_nova", "ChatAmazonNova"),
}

def build_provider_model():
    try:
        config = json.loads(PROVIDER_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    provider = str(config.get("provider") or "").strip()
    model = str(config.get("model") or "").strip()
    if not provider or not model:
        return None

    kwargs = {"model": model}
    api_key = str(config.get("api_key") or "").strip()
    if api_key and provider != "ollama":
        kwargs["api_key"] = api_key

    harness = PROVIDER_HARNESSES.get(provider)
    if harness:
        return init_chat_model(model_provider=harness, **kwargs)

    target = PROVIDER_CLASSES.get(provider)
    if not target:
        return None
    module = import_module(target[0])
    return getattr(module, target[1])(**kwargs)
MAIN_MODEL= build_provider_model()
# directory that file system tool has access to (dedicated agent sandbox)
PROJECT_ROOT = Path.home() / ".Charles"

#(not yet fully implemented) read-only directories the agent can look into but never write to
READONLY_PATHS: list[Path] = [
    Path.home() / "Documents",
]

#(not yet fully implemented) high risk tools that require approval
REQUIRE_APPROVAL: set[str] = {
    "send_email",
    "delete_file",
    "run_shell_command",
    "create_calendar_event",
    "send_message",
}
# Persistence

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "database.db"
CHROMA_PERSIST_DIR = Path(__file__).resolve().parent.parent / "chroma_langchain_db"

# Retrieval

EMBEDDING_MODEL_CONTEXT=int(os.getenv("EMBEDDING_MODEL_CONTEXT", 512))
EMBEDDING_MODEL_CHUNK=int(os.getenv("EMBEDDING_MODEL_CHUNK", 64))
RAG_TOP_K = 4

# Web tool limits (not yet implemented)

WEB_SEARCH_MAX_RESULTS = 5
WEB_FETCH_TIMEOUT_SECONDS = 15

#MCP urls
BROWSER_OS_URL="http://127.0.0.1:9010/mcp"

#other env vars
WEB_ENABLED=os.getenv("WEB_ENABLED")
DESKTOP_ENABLED=os.getenv("DESKTOP_ENABLED")
