import asyncio

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from tools.tools import tool_list
from config.settings import DB_PATH, ENABLED_TOOLS, PROJECT_ROOT, MAIN_MODEL, ENABLED_SUBAGENTS
from agent.system_prompt import build_system_prompt
from subagents.web import web_agent
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend, CompositeBackend, StateBackend, StoreBackend
from langgraph.store.sqlite.aio import AsyncSqliteStore
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

DB_PATH.parent.mkdir(parents=True, exist_ok=True)
PROJECT_ROOT.mkdir(parents=True, exist_ok=True)


class DeepAgent:
    def __init__(self) -> None:
        self.build_lock: asyncio.Lock | None = None
        self.checkpointer_cm = None
        self.store_cm = None
        self.checkpointer = None
        self.store = None
        self.agent = None

    async def build(self):
        if self.agent is not None:
            return self.agent
        if self.build_lock is None:
            self.build_lock = asyncio.Lock()
        async with self.build_lock:
            if self.agent is not None:
                return self.agent
            self.checkpointer_cm = AsyncSqliteSaver.from_conn_string(DB_PATH)
            self.checkpointer = await self.checkpointer_cm.__aenter__()
            self.store_cm = AsyncSqliteStore.from_conn_string(DB_PATH)
            self.store = await self.store_cm.__aenter__()
            await self.store.setup()
            self.agent = await asyncio.to_thread(
                construct_agent,
                tool_list,
                self.store,
                self.checkpointer,
            )
        return self.agent

def construct_agent(tools, store, checkpointer):
    backend = CompositeBackend(
        default=StateBackend(),
        routes={
            "/longtermmemories/": StoreBackend(
                store=store,
                namespace=lambda op: ("localAgent", "longterm"),
            ),
            "/project/": FilesystemBackend(root_dir=PROJECT_ROOT, virtual_mode=True),
        },
    )
    return create_deep_agent(
        model=MAIN_MODEL,
        system_prompt=build_system_prompt(ENABLED_TOOLS, ENABLED_SUBAGENTS),
        memory=["/longtermmemories/AGENTS.md"],
        tools=tools,
        backend=backend,
        store=store,
        checkpointer=checkpointer,
        subagents=[web_agent] if web_agent is not None else None,
    )

deep_agent = DeepAgent()
#variable required for langgraph server
stack_agent = deep_agent.build

#Function for local cli usage
async def build_agent():
    return await deep_agent.build()

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
    async for checkpoint in deep_agent.checkpointer.alist(None,limit=limit):
        thread_id=checkpoint.config["configurable"]["thread_id"]
        if thread_id in threads:
            continue
        thread_item = await deep_agent.store.aget(("localAgent", "thread_names"), thread_id)
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
            await deep_agent.store.aput(
                ("localAgent", "thread_names"),
                thread_id,
                {"name": thread_name},
            )
        except Exception:
            pass
#cli response method
async def response(message: str, thread_id:str):
    agent = await build_agent()
    config={"configurable": {"thread_id":thread_id}}
    state = await agent.ainvoke({"messages": [{"role": "user", "content": message}]},config=config)
    if not extract_answer(state):
        followup = {"role": "user", "content": EMPTY_RESPONSE_FOLLOWUP}
        state = await agent.ainvoke({"messages": [*state.get("messages", []), followup]},config=config)
    final = extract_answer(state) or FALLBACK_RESPONSE
    last = state.get("messages", [])[-1]
    if isinstance(last, AIMessage):
        last.content = final
        last.tool_calls = []
        last.tool_call_chunks = []
    await thread_renamer(state,thread_id)
    return state