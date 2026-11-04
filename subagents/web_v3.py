import asyncio
import os
import re
import shlex
import shutil
import sys
from functools import cache
from pathlib import Path
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.tools import ToolRuntime, tool
from deepagents import CompiledSubAgent
from config.settings import (
    BROWSER_ACT_COMMANDS,
    BROWSER_COMMAND_TIMEOUT,
    BROWSER_EXECUTABLE_CANDIDATES,
    BROWSER_EXECUTABLE_ENV,
    BROWSER_EXECUTABLE_NAMES,
    BROWSER_FORBIDDEN_FLAGS,
    BROWSER_IDLE_TIMEOUT,
    BROWSER_MAX_OUTPUT,
    BROWSER_READ_COMMANDS,
    WEB_ENABLED,
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def agent_browser_binary():
    return os.getenv("AGENT_BROWSER_BIN") or shutil.which("agent-browser")


@cache
def ensure_agent_browser():
    if not WEB_ENABLED:
        return False
    ready = bool(agent_browser_binary())
    if not ready:
        print("agent-browser not installed")
    return ready

def browser_session(runtime: ToolRuntime) -> str:
    config = runtime.config or {}
    configurable = config.get("configurable") or {}
    thread_id = str(configurable.get("thread_id") or "default")
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "-", thread_id)[:80]
    return f"charles-{safe_id}"


def is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def browser_executable() -> str | None:
    configured = os.getenv(BROWSER_EXECUTABLE_ENV)
    if configured:
        candidate = Path(configured).expanduser()
        if is_executable(candidate):
            return str(candidate)
    for candidate in BROWSER_EXECUTABLE_CANDIDATES:
        if is_executable(Path(candidate)):
            return candidate
    for name in BROWSER_EXECUTABLE_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def browser_env() -> dict:
    env = {
        **os.environ,
        "AGENT_BROWSER_CONTENT_BOUNDARIES": "1",
        "AGENT_BROWSER_MAX_OUTPUT": str(BROWSER_MAX_OUTPUT),
        "AGENT_BROWSER_IDLE_TIMEOUT": BROWSER_IDLE_TIMEOUT,
    }
    executable = browser_executable()
    if executable:
        env[BROWSER_EXECUTABLE_ENV] = executable
    return env


async def run_browser_process(args: list[str]) -> tuple[int | None, str, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=browser_env(),
        )
    except OSError as error:
        return 1, "", f"agent-browser failed to start: {error}"

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=BROWSER_COMMAND_TIMEOUT
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return None, "", "agent-browser timed out."

    return (
        process.returncode,
        stdout.decode("utf-8", errors="replace").strip(),
        stderr.decode("utf-8", errors="replace").strip(),
    )


async def run_browser(command: str, allowed: set[str], runtime: ToolRuntime) -> str:
    if not ensure_agent_browser():
        return "agent-browser not installed."

    try:
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
        if part.split("=", 1)[0] in BROWSER_FORBIDDEN_FLAGS:
            return f"Forbidden flag: {part}"

    binary = agent_browser_binary()
    args = [
        binary,
        "--session",
        browser_session(runtime),
        "--content-boundaries",
        "--max-output",
        str(BROWSER_MAX_OUTPUT),
        *parts,
    ]

    # Retry first open; Opera GX aborts once.
    attempts = 2 if verb == "open" else 1
    for attempt in range(attempts):
        returncode, output, error_output = await run_browser_process(args)
        if returncode is None:
            return error_output
        if returncode == 0:
            break
        detail = error_output or output or "no output"
        if attempt + 1 < attempts and "ERR_ABORTED" in detail:
            continue
        return f"agent-browser failed ({returncode}): {detail}"

    if not output:
        return error_output or "agent-browser returned no output."
    if len(output) > BROWSER_MAX_OUTPUT:
        return output[:BROWSER_MAX_OUTPUT] + "\n[truncated]"
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
    if not ensure_agent_browser():
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
