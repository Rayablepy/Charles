import shutil
from langchain_core.tools import tool
from subagents.sandbox import check_sandbox_server
from subagents.web_v3 import ensure_agent_browser

#May have actual checks on connection-bound tools in the future, tbc
@tool
def check_tool_status()->dict[str,bool]:
    """Use this tool to check the availability of tools that are not available by default.
    Args:
        None
    Returns:
        dict[str,bool]: The non-default tools currently available to you."""
    tool_status = {
    "rag": True,
    "filesystem": True,
    "todo": True,
    }
    return tool_status

@tool
async def check_subagent_status()->dict[str,bool]:
    """Use this tool to check the subagents available to you.
    Args:
        None
    Returns:`
        dict[str,bool]: The subagents available to you.`"""
    subagent_status = {
        "web_agent": False,
        "sandbox_agent": False,
                       }
    web_status = ensure_agent_browser()
    sandbox_status = check_sandbox_server() or shutil.which("uvx") is not None
    if web_status: 
        subagent_status["web_agent"] = True
    if sandbox_status:
        subagent_status["sandbox_agent"] = True
    return subagent_status

check_tool_list=[check_tool_status,check_subagent_status]
