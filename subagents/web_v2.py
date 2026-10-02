import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WEB_TOOLS_STATUS = None
SESSION_CTX_MANAGER = None
CLIENT_CTX_MANAGER = None

async def initialise_web_mcp():
    global WEB_TOOLS_STATUS, SESSION_CTX_MANAGER, CLIENT_CTX_MANAGER
    server_params = StdioServerParameters(
        command="uvx",
        args=["--from", "browser-use[cli]", "browser-use", "--mcp"],
    )
    try:
        SESSION_CTX_MANAGER = stdio_client(server_params)
        read, write = await SESSION_CTX_MANAGER.__aenter__()
        CLIENT_CTX_MANAGER = ClientSession(read, write)
        await CLIENT_CTX_MANAGER.__aenter__()
        await CLIENT_CTX_MANAGER.initialize()
        WEB_TOOLS_STATUS = True
    except Exception as error:
        print(f"init failed: {error!r}")
        await close_web_tools()


async def get_web_tools():
    if not WEB_TOOLS_STATUS or CLIENT_CTX_MANAGER is None:
        return []
    try:
        result = await CLIENT_CTX_MANAGER.list_tools()
        return list(result.tools)
    except Exception as error:
        print(f"list_tools failed: {error!r}")
        return []
async def close_web_tools():
    global CLIENT_CTX_MANAGER, SESSION_CTX_MANAGER, WEB_TOOLS_STATUS
    WEB_TOOLS_STATUS = False
    if CLIENT_CTX_MANAGER:
        try:
            await CLIENT_CTX_MANAGER.__aexit__(None, None, None)
        except Exception:
            pass
        CLIENT_CTX_MANAGER = None
    if SESSION_CTX_MANAGER:
        try:
            await SESSION_CTX_MANAGER.__aexit__(None, None, None)
        except Exception:
            pass
        SESSION_CTX_MANAGER = None

async def load_web_tools():
    await initialise_web_mcp()
    tools = await get_web_tools()
    await close_web_tools()
    return tools


web_tools = asyncio.run(load_web_tools())
print(web_tools)
