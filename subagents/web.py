import sys
from pathlib import Path
from langchain.agents import create_agent

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asyncio
from deepagents import SubAgent, CompiledSubAgent
from langchain.mcp import MCPAdapter
from config.settings import BROWSER_OS_URL, LOCAL_MODEL, MAIN_MODEL

WEB_TOOLS_STATUS=None
async def get_web_tools()->list:
    global WEB_TOOLS_STATUS
    try:
        async with MCPAdapter(BROWSER_OS_URL) as mcp:
            web_tools= await mcp.list_tools()
            WEB_TOOLS_STATUS=True
            return web_tools
    except Exception:
        WEB_TOOLS_STATUS=False
        return []
web_tools=asyncio.run(get_web_tools())
if WEB_TOOLS_STATUS and web_tools:
    web_graph = create_agent(
        model=LOCAL_MODEL if LOCAL_MODEL is not None else MAIN_MODEL,
        name="web_agent",
        tools=web_tools,
        system_prompt="""You are a basic agent meant only to execute tasks on the web explicitly as instructed.
        Do not execute high-risk actions such as sending emails, messages or submitting forms.
        Instead, return a clearly-marked [APPROVAL REQUIRED] block to the user.
        Otherwise,return the results of your work.
        """
    )
    web_agent = CompiledSubAgent(
        name="web_agent",
        description="Handles any web related tasks the user requires. Ensure instructions are clear and precise. Returns results of its work.",
        runnable=web_graph
    )
else:
    web_agent=None