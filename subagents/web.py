'''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
'''
import asyncio

from deepagents import SubAgent
from langchain.mcp import MCPAdapter
from config.settings import BROWSER_OS_URL, LOCAL_MODEL, MAIN_MODEL

WEB_TOOLS_STATUS=None
async def get_web_tools()->list:
    try:
        async with MCPAdapter(BROWSER_OS_URL) as mcp:
            web_tools= await mcp.list_tools()
            WEB_TOOLS_STATUS=True
            return web_tools
    except:
        WEB_TOOLS_STATUS=False
        return []

web_agent=SubAgent(
    model=LOCAL_MODEL if LOCAL_MODEL is not None else MAIN_MODEL,
    name="basic_web_agent",
    description="Handles any web related tasks the user requires. Ensure instructions are clear and precise. Returns results of its work.",
    tools=asyncio.run(get_web_tools()),
    system_prompt="You are a basic agent meant only to execute tasks on the web explicitly as instructed.Return the results of your work."
)