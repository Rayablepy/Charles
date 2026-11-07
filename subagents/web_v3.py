import asyncio
import re
import shlex
import shutil
import sys
from functools import cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.tools import ToolRuntime, tool
from deepagents import CompiledSubAgent
from config.settings import (
    BROWSER_ACT_COMMANDS,
    BROWSER_COMMAND_TIMEOUT,
    BROWSER_FORBIDDEN_FLAGS,
    BROWSER_MAX_OUTPUT,
    BROWSER_READ_COMMANDS,
    WEB_ENABLED,
)

@cache
def ensure_agent_browser():
    installed = shutil.which("agent-browser") is not None
    if not installed:
        print("agent-browser not installed")
    return installed

def browser_session(runtime: ToolRuntime) -> str:
    config = runtime.config or {}
    configurable = config.get("configurable") or {}
    thread_id = str(configurable.get("thread_id") or "default")
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "-", thread_id)[:80]
    return f"charles-{safe_id}"


async def run_browser(command: str, allowed: set[str], runtime: ToolRuntime) -> str:
    if not ensure_agent_browser():
        return "agent-browser not installed."
    try:
        #split input command into individual command segment strs
        parts = shlex.split(command)
    except ValueError as error:
        return f"Invalid command: {error}"
    if not parts:
        return "Empty command."

    verb = parts[0].lower()
    if verb not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        return f"Unsupported command '{verb}'. Allowed: {allowed_list}"

    for part in parts[1:]:
        flag = part.split("=", 1)[0]
        #detect forbidden flag in command
        if flag in BROWSER_FORBIDDEN_FLAGS and not (verb == "snapshot" and flag == "-s"):
            return f"Forbidden flag: {part}"
    #filter elements in output using the flags
    snapshot_flags = {
        "-i",
        "--interactive",
        "-c",
        "--compact",
        "-s",
        "--selector",
        "-d",
        "--depth",
        "--delta",
    }
    #add filters only if none were provided(optimise token usage)
    if verb == "snapshot" and not any(part.split("=", 1)[0] in snapshot_flags for part in parts[1:]):
        parts.extend(["-i", "-c"])
    #agent browser cli start script
    args = [
        "agent-browser",
        "--session",
        browser_session(runtime),
        "--content-boundaries",
        "--max-output",
        str(BROWSER_MAX_OUTPUT),
        *parts,
    ]

    try:
        #start agent browser subprocess
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as error:
        return f"agent-browser failed to start: {error}"

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=BROWSER_COMMAND_TIMEOUT
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return "agent-browser timed out."
    #parse errors and output
    output = stdout.decode("utf-8", errors="replace").strip()
    error_output = stderr.decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        detail = error_output or output or "no output"
        return f"agent-browser failed ({process.returncode}): {detail}"
    if not output:
        return error_output or "agent-browser returned no output."
    if len(output) > BROWSER_MAX_OUTPUT:
        cut = output.rfind("\n", 0, BROWSER_MAX_OUTPUT)
        if cut < 1:
            cut = BROWSER_MAX_OUTPUT
        return output[:cut].rstrip() + "\n[truncated at line boundary; narrow the command]"
    return output


@tool
async def browser_read(command: str, runtime: ToolRuntime) -> str:
    """Run a read-only agent-browser command."""
    return await run_browser(command, BROWSER_READ_COMMANDS, runtime)


@tool
async def browser_act(command: str, runtime: ToolRuntime) -> str:
    """Run an interactive agent-browser command."""
    return await run_browser(command, BROWSER_ACT_COMMANDS, runtime)


async def build_web_agent(model, checkpointer=None):
    if not WEB_ENABLED or not ensure_agent_browser():
        return None
    middleware = []
    if checkpointer is not None:
        middleware.append(
            HumanInTheLoopMiddleware(
                interrupt_on={"browser_act": True},
                description_prefix="Browser action requires approval",
            )
        )
    web_graph = create_agent(
        model=model,
        name="web_agent",
        tools=[browser_read, browser_act],
        middleware=middleware,
        checkpointer=checkpointer,
        system_prompt="""You control a browser through agent-browser.
        Use browser_read for open, snapshot, get, wait, and navigation.
        Use browser_act for click, fill, type, press, select, and scrolling.
        Run snapshot before acting and after every page change.
        Use @eN refs from the latest snapshot.
        Never use eval, uploads, downloads, cookies, storage, or profiles.
        Do not execute high-risk actions such as sending messages or submitting forms.
        Instead, return a clearly-marked [APPROVAL REQUIRED] block to the user.
        When passwords and/or credentials are needed, raise a [CREDENTIAL REQUIRED] block.
        Otherwise, return the results of your work.
        """,
    )
    return CompiledSubAgent(
        name="web_agent",
        description="Handles any web related tasks the user requires. Ensure instructions are clear and precise. Returns results of its work.",
        runnable=web_graph,
    )
