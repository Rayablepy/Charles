import os
from dotenv import load_dotenv
from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_openrouter import ChatOpenRouter

load_dotenv()

#tool list that agent will have access to, update when tools are added or removed
ENABLED_TOOLS: list[str] = [
    "rag",
    "todo/notes",
    # "calendar",
    "web",
    "web_basic",
]
ENABLED_SUBAGENTS: list[str] = [
    "basic_web"
]

#Model constants
CHAT_MODEL_NAME=os.getenv("CHAT_MODEL_NAME")
OPENROUTER_CHAT_MODEL_NAME="openrouter/free"
OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
LOCAL_MODEL_NAME=os.getenv("LOCAL_MODEL_NAME")
LOCAL_EMBEDDING_MODEL_NAME=os.getenv("LOCAL_EMBEDDING_MODEL_NAME")
MODEL_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_PROVIDER = "openai"
LOCAL_MODEL_BASE_URL = "http://localhost:1234/v1"


LOCAL_MODEL= init_chat_model(
    model=LOCAL_MODEL_NAME,
    model_provider=MODEL_PROVIDER,
    base_url=LOCAL_MODEL_BASE_URL,
    api_key=OPENROUTER_API_KEY, #this can be anything but i am just using the existing api key var
)

MAIN_MODEL = ChatOpenRouter(
    model=OPENROUTER_CHAT_MODEL_NAME,
    base_url=MODEL_BASE_URL,
    api_key=OPENROUTER_API_KEY,
    openrouter_provider={"max_price": {"prompt": 0, "completion": 0}},
)

# directory that file system tool has access to (dedicated agent sandbox)
PROJECT_ROOT = Path.home() / "agent_project"

#(not yet fully implemented) read-only directories the agent can look into but never write to
READONLY_PATHS: list[Path] = [
    Path.home() / "Documents",
]

#high risk tools that require approval
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
