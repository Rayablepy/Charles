
import os
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastmcp.client.transports.stdio import StdioTransport
from langchain.agents import create_agent
from langchain.mcp import MCPAdapter
from langchain_core.tools import tool
from deepagents import CompiledSubAgent
from config.settings import LOCAL_MODEL, MAIN_MODEL, DESKTOP_ENABLED

DESKTOP_TOOLS_STATUS = None
desktop_tools: list = []


def desktop_binary() -> str:
    # venv script avoids a uvx resolve on every tool call
    local = Path(sys.executable).with_name(
        "xa11y.exe" if sys.platform == "win32" else "xa11y"
    )
    return str(local) if local.exists() else "xa11y"


async def ensure_desktop_mcp() -> bool:
    global DESKTOP_TOOLS_STATUS, desktop_tools
    if not DESKTOP_ENABLED:
        return False
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

@tool
def launch_app(name: str):
    """Launch a desktop application by name or executable path.
    Args:
        name (str): Application or executable name, for example, 'calc.exe' or 'notepad.exe'.
    Returns:
        str: Whether the launch was requested or why it failed.
    """
    # xa11y only drives running apps, so launching stays native
    try:
        if sys.platform == "win32":
            os.startfile(name)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", name])
        else:
            subprocess.Popen([name])
        return f"Launch requested for {name}"
    except OSError as error:
        return f"Launch failed for {name}: {error}"

async def build_desktop_agent():
    await ensure_desktop_mcp()
    if not DESKTOP_TOOLS_STATUS or not desktop_tools:
        return None
    desktop_graph = create_agent(
        model=LOCAL_MODEL if LOCAL_MODEL is not None else MAIN_MODEL,
        name="desktop_controller_agent",
        tools=[*desktop_tools, launch_app],
        system_prompt="""You are a basic agent meant only to execute tasks on the user's desktop interface explicitly as instructed.
        Use launch_app to start an application that is not already running.
        Work in this order: apps -> tree (max_depth 2 to 3) -> find -> action.
        Prefer action over click, since it uses the application's own accessibility action.
        Re-read the tree after acting when the effect matters.
        Do not execute high-risk actions such as opening and utilising terminal windows, or unauthorised applications.
        Instead, return a clearly-marked [APPROVAL REQUIRED] block to the user.
        Otherwise,return the results of your work.
        """,
    )
    return CompiledSubAgent(
        name="desktop_controller_agent",
        description="Handles any tasks the user requires that involves direct control of their desktop interface."
                    "Ensure instructions are clear and precise. Returns results of its work.",
        runnable=desktop_graph,
    )
