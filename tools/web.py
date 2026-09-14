'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
'''
import asyncio
from langchain.mcp import MCPAdapter
from config.settings import BROWSER_OS_URL

async def get_web_tools():
    async with MCPAdapter(BROWSER_OS_URL) as mcp:
        web_tools= await mcp.list_tools()
        return web_tools