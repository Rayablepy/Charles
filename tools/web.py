'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
'''
import asyncio
from langchain.mcp import MCPAdapter
from config.settings import BROWSER_OS_URL

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