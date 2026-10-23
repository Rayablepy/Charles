
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp.client.transports.stdio import StdioTransport
from langchain.mcp import MCPAdapter

DESKTOP_TOOLS_STATUS = None
desktop_tools= []


def desktop_binary() -> str:
    local = Path(sys.executable).with_name(
        "xa11y.exe" if sys.platform == "win32" else "xa11y"
    )
    return str(local) if local.exists() else "xa11y"


async def ensure_desktop_mcp() -> bool:
    global DESKTOP_TOOLS_STATUS, desktop_tools
    if DESKTOP_TOOLS_STATUS is True:
        return True
    try:
        transport = StdioTransport(command=desktop_binary(), args=["mcp"])
        adapter = MCPAdapter(transport)
        loaded = await adapter.list_tools()
        if not loaded:
            DESKTOP_TOOLS_STATUS = False
            return False
        desktop_tools = loaded
        DESKTOP_TOOLS_STATUS = True
        return True
    except Exception as error:
        print(f"desktop mcp init failed: {error}")
        DESKTOP_TOOLS_STATUS = False
        return False
