from langchain_core.tools import tool
from config.settings import SANDBOX_ENABLED, WEB_ENABLED, subagent_enabled
from subagents.sandbox import sandbox_available
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
    web_status = subagent_enabled("web_agent", WEB_ENABLED) and ensure_agent_browser()
    sandbox_status = subagent_enabled("sandbox_agent", SANDBOX_ENABLED) and sandbox_available()
    if web_status: 
        subagent_status["web_agent"] = True
    if sandbox_status:
        subagent_status["sandbox_agent"] = True
    return subagent_status

check_tool_list=[check_tool_status,check_subagent_status]
