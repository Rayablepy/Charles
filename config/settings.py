import hashlib
import json
import os
from dotenv import load_dotenv
from importlib import import_module
from pathlib import Path

from langchain.chat_models import init_chat_model

load_dotenv()

#Model constants
CHAT_MODEL_NAME=os.getenv("CHAT_MODEL_NAME")
LOCAL_MODEL_NAME=os.getenv("LOCAL_MODEL_NAME")
LOCAL_EMBEDDING_MODEL_NAME=os.getenv("LOCAL_EMBEDDING_MODEL_NAME")
MODEL_PROVIDER = "openai"
LOCAL_MODEL_BASE_URL = "http://localhost:1234/v1"

PROJECT_ROOT = Path.home() / ".Charles"
PROVIDER_CONFIG_PATH = PROJECT_ROOT / "provider.json"
'''
if LOCAL_MODEL_NAME:
    LOCAL_MODEL= init_chat_model(
        model=LOCAL_MODEL_NAME,
        model_provider=MODEL_PROVIDER,
        base_url=LOCAL_MODEL_BASE_URL,
        api_key="smth", #this can be anything
    )
else:
    LOCAL_MODEL= None
'''
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

MODEL_PARAM_NAMES = ("temperature", "max_tokens", "timeout", "max_retries", "base_url")

#hash saved provider details
def provider_config_signature():
    try:
        return hashlib.sha256(PROVIDER_CONFIG_PATH.read_bytes()).hexdigest()
    except OSError:
        return None

def read_provider_configs():
    try:
        configs = json.loads(PROVIDER_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(configs, list):
        return []
    return [config for config in configs if isinstance(config, dict)]

def find_provider_config(configs, provider_name=None):
    if provider_name is None:
        return next((item for item in configs if item.get("active") is True), None)
    return next(
        (item for item in configs if str(item.get("provider") or "").strip() == provider_name),
        None,
    )

def build_provider_model():
    config = find_provider_config(read_provider_configs())
    if config is None:
        return None

    provider = str(config.get("provider") or "").strip()
    model = str(config.get("model") or "").strip()
    api_key = str(config.get("api_key") or "").strip()
    if not provider or not model:
        return None
    if not api_key and provider != "ollama":
        return None

    params = {}
    if api_key:
        params["api_key"] = api_key
    for name in MODEL_PARAM_NAMES:
        if config.get(name) is not None:
            params[name] = config[name]
    harness = PROVIDER_HARNESSES.get(provider)
    if harness:
        return init_chat_model(model=model, model_provider=harness, **params)
    target = PROVIDER_CLASSES.get(provider)
    if not target:
        return None
    module = import_module(target[0])
    return getattr(module, target[1])(model=model, **params)

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

# Browser CLI limits and safety

BROWSER_MAX_OUTPUT = int(os.getenv("BROWSER_MAX_OUTPUT", "20000"))
BROWSER_COMMAND_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "90"))

BROWSER_IDLE_TIMEOUT = os.getenv("BROWSER_IDLE_TIMEOUT", "3600")
BROWSER_READ_COMMANDS = {
    "read",
    "open",
    "snapshot",
    "get",
    "is",
    "wait",
    "back",
    "forward",
    "reload",
    "close",
    "tab-list",
}

BROWSER_ACT_COMMANDS = {
    "click",
    "dblclick",
    "fill",
    "type",
    "press",
    "select",
    "check",
    "uncheck",
    "hover",
    "focus",
    "scroll",
    "drag",
    "tab-new",
    "tab-select",
    "tab-close",
}

BROWSER_FORBIDDEN_FLAGS = {
    "-p",
    "-s",
    "--action-policy",
    "--allow-file-access",
    "--allowed-domains",
    "--args",
    "--auto-connect",
    "--ca-cert",
    "--cdp",
    "--cdp-headers",
    "--cdp-url",
    "--config",
    "--confirm-actions",
    "--confirm-interactive",
    "--device",
    "--download-path",
    "--engine",
    "--enable",
    "--executable-path",
    "--extension",
    "--idle-timeout",
    "--ignore-https-errors",
    "--init-script",
    "--max-output",
    "--model",
    "--no-ca-cert",
    "--profile",
    "--provider",
    "--proxy",
    "--proxy-bypass",
    "--restore",
    "--screenshot-dir",
    "--session",
    "--session-name",
    "--state",
    "--use-system-ca",
    "--user-agent",
    "--user-data-dir",
}

#other env vars
WEB_ENABLED=os.getenv("WEB_ENABLED")
DESKTOP_ENABLED=os.getenv("DESKTOP_ENABLED")
