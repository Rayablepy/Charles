import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from langchain.agents import create_agent
import asyncio
from deepagents import SubAgent, CompiledSubAgent
from langchain.mcp import MCPAdapter
from config.settings import BROWSER_OS_URL, LOCAL_MODEL, MAIN_MODEL
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WEB_TOOLS_STATUS=None
SESSION_CTX_MANAGER=None
CLIENT_CTX_MANAGER=None
async def initialise_web_mcp():
    global WEB_TOOLS_STATUS, SESSION_CTX_MANAGER, CLIENT_CTX_MANAGER
    server_params = StdioServerParameters(
        command="uvx",
        args=["--from", "browser-use[cli]", "browser-use", "--mcp"]
    )
    try:
        SESSION_CTX_MANAGER=stdio_client(server_params=server_params)
        read,write = await SESSION_CTX_MANAGER.__aenter__()
        CLIENT_CTX_MANAGER=ClientSession(read,write)
        await CLIENT_CTX_MANAGER.__aenter__()
        await CLIENT_CTX_MANAGER.initialize()
        WEB_TOOLS_STATUS=True

    except Exception:
        WEB_TOOLS_STATUS=False
        return []

web_tools=asyncio.run(get_web_tools())
print(web_tools)
