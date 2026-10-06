from langchain_core.tools import tool
from subagents.web_v2 import ensure_web_mcp

#May have actual checks on connection-bound tools in the future, tbc
@tool
def check_tool_status()->dict[str,bool]:
    """Use this tool to check the tools currently available to you.
    Args:
        None
    Returns:
        dict[str,bool]: The tools currently available to you."""
    tool_status = {
    "rag": True,
    "filesystem": True,
    "todo/notes": True,
    #Include tools provided by langchain middleware
    "ls": True,
    "read_file": True,
    "write_file": True,
    "edit_file": True,
    "glob": True,
    "grep": True,
    "write_todos": True
    }
    return tool_status

@tool
async def check_subagent_status()->dict[str,bool]:
    """Use this tool to check the subagents available to you.
    Args:
        None
    Returns:`
        dict[str,bool]: The subagents available to you.`"""
    web_status = await ensure_web_mcp()
    if web_status:
        subagent_status = {"web_agent": True}
    else:
        subagent_status = {"web_agent": False}
    return subagent_status

check_tool_list=[check_tool_status,check_subagent_status]
