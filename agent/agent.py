import asyncio

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from tools.tools import tool_list
from config.settings import ENABLED_TOOLS, PROJECT_ROOT, MODEL_BASE_URL, MODEL_PROVIDER, LOCAL_MODEL_NAME, \
    LOCAL_MODEL_BASE_URL
from agent.system_prompt import build_system_prompt
from config.settings import OPENROUTER_CHAT_MODEL_NAME, DB_PATH, OPENROUTER_API_KEY
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend,CompositeBackend,StateBackend, StoreBackend
from langgraph.store.sqlite.aio import AsyncSqliteStore
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

DB_PATH.parent.mkdir(parents=True,exist_ok=True)
PROJECT_ROOT.mkdir(parents=True,exist_ok=True)

model = ChatOpenRouter(
    model=OPENROUTER_CHAT_MODEL_NAME,
    base_url=MODEL_BASE_URL,
    api_key=OPENROUTER_API_KEY,
    openrouter_provider={"max_price": {"prompt": 0, "completion": 0}},
)
#general purpose light model for small scale tasks
'''
local_model= init_chat_model(
    model=LOCAL_MODEL_NAME,
    model_provider=MODEL_PROVIDER,
    base_url=LOCAL_MODEL_BASE_URL,
    api_key=OPENROUTER_API_KEY, #this can be anything but i am just using the existing api key var
)
'''
checkpointer=None
checkpointer_context_manager=None
store = None
store_context_manager = None
backend=None
agent=None

async def build_agent():
    global checkpointer
    global checkpointer_context_manager
    global store
    global store_context_manager
    global backend
    global agent
    if agent:
        return agent
    checkpointer_context_manager = AsyncSqliteSaver.from_conn_string(DB_PATH)
    checkpointer=await checkpointer_context_manager.__aenter__()
    store_context_manager = AsyncSqliteStore.from_conn_string(DB_PATH)
    store = await store_context_manager.__aenter__()
    await store.setup()
    backend=CompositeBackend(
            default=StateBackend(),
            routes={
                "/longtermmemories/": StoreBackend(store=store,namespace=lambda _: ("localAgent","longterm")),
                "/project/": FilesystemBackend(root_dir=PROJECT_ROOT,virtual_mode=True)
            }
        )
    agent = create_deep_agent(
        model=model,
        system_prompt=build_system_prompt(ENABLED_TOOLS),
        memory=["/longtermmemories/AGENTS.md"],
        tools=tool_list,
        backend=backend,
        store=store,
        checkpointer=checkpointer,
    )

    return agent

#parser for potential empty responses
EMPTY_RESPONSE_FOLLOWUP = (
    "Your previous response was empty. "
    "Please reply to my request now with a written answer."
)
FALLBACK_RESPONSE = "I wasn't able to generate a response. Please rephrase or try again."


def text_builder(blocks):
    texts = []
    for block in blocks:
        if isinstance(block, str):
            if block.strip():
                texts.append(block)
        elif isinstance(block, dict):
            btype = block.get("type")
            if btype in ("text", "thinking", "reasoning") and isinstance(block.get("text"), str) and block["text"].strip():
                texts.append(block["text"])
            elif btype == "reasoning" and isinstance(block.get("summary"), list):
                for s in block["summary"]:
                    if isinstance(s, str) and s.strip():
                        texts.append(s)
                    elif isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip():
                        texts.append(s["text"])
    return "\n".join(texts).strip()


def message_text(m):
    content = getattr(m, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        text = text_builder(content)
        if text:
            return text
    content_blocks = getattr(m, "content_blocks", None)
    if content_blocks:
        text = text_builder(content_blocks)
        if text:
            return text
    extra = getattr(m, "additional_kwargs", None) or {}
    for key in ("reasoning_content", "reasoning_details"):
        val = extra.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""

def extract_answer(state):
    for m in reversed(state.get("messages", [])):
        if isinstance(m, (HumanMessage, SystemMessage)):
            continue
        text = message_text(m)
        if text:
            return text
    return ""

#helper method to get a list of threads
async def list_threads(limit: int = 50)->dict:
    await build_agent()
    threads = {}
    async for checkpoint in checkpointer.alist(None,limit=limit):
        thread_id=checkpoint.config["configurable"]["thread_id"]
        if thread_id in threads:
            continue
        thread_item = await store.aget(("localAgent", "thread_names"), thread_id)
        thread_name = thread_item.value["name"] if thread_item else None
        if not thread_name:
            thread_name="Untitled Chat"
        threads[thread_id] = thread_name
    return threads

async def thread_renamer(state,thread_id):
    messages = state.get("messages", [])
    if len(messages) == 2:
        try:
            thread_name=thread_id[:8]
            await store.aput(
                ("localAgent", "thread_names"),
                thread_id,
                {"name": thread_name},
            )
        except Exception:
            pass
#main response method
async def response(message: str, thread_id:str):
    agent = await build_agent()
    config={"configurable": {"thread_id":thread_id}}
    state = await agent.ainvoke({"messages": [{"role": "user", "content": message}]},config=config)
    if not extract_answer(state):
        followup = {"role": "user", "content": EMPTY_RESPONSE_FOLLOWUP}
        state = await agent.ainvoke({"messages": [*state.get("messages", []), followup]})
    final = extract_answer(state) or FALLBACK_RESPONSE
    last = state.get("messages", [])[-1]
    if isinstance(last, AIMessage):
        last.content = final
        last.tool_calls = []
        last.tool_call_chunks = []
    await thread_renamer(state,thread_id)
    return state