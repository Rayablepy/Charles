
from fastmcp.client.transports.stdio import StdioTransport
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from deepagents import CompiledSubAgent
from config.settings import LOCAL_MODEL, MAIN_MODEL
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

WEB_TOOLS_STATUS = None
web_tools: list = []


async def ensure_web_mcp():
    global WEB_TOOLS_STATUS, web_tools
    if WEB_TOOLS_STATUS is True:
        return
    try:
        transport = StdioTransport(
            command="uvx",
            args=["--from", "browser-use[cli]", "browser-use", "--mcp"],
        )
        adapter = MCPAdapter(transport)
        loaded = await adapter.list_tools()
        if not loaded:
            WEB_TOOLS_STATUS = False
            return
        web_tools = loaded
        WEB_TOOLS_STATUS = True
    except Exception as error:
        print(f"web mcp init failed: {error}")
        WEB_TOOLS_STATUS = False


async def build_web_agent():
    await ensure_web_mcp()
    if not WEB_TOOLS_STATUS or not web_tools:
        return None
    web_graph = create_agent(
        model=LOCAL_MODEL if LOCAL_MODEL is not None else MAIN_MODEL,
        name="web_agent",
        tools=web_tools,
        system_prompt="""You are a basic agent meant only to execute tasks on the web explicitly as instructed.
        Do not execute high-risk actions such as sending emails, messages or submitting forms.
        Instead, return a clearly-marked [APPROVAL REQUIRED] block to the user.
        Otherwise,return the results of your work.
        """,
    )
    return CompiledSubAgent(
        name="web_agent",
        description="Handles any web related tasks the user requires. Ensure instructions are clear and precise. Returns results of its work.",
        runnable=web_graph,
    )
