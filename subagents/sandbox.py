import importlib.util
import json
import shutil
import sys
import time
from contextlib import asynccontextmanager
from functools import cache
from pathlib import Path
import urllib.request
import signal
import subprocess
import os
import asyncio
from typing import Any, TypedDict
from langchain_core.runnables import RunnableLambda
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from deepagents import CompiledSubAgent
from langchain.tools import ToolRuntime, tool
from langchain.agents import create_agent
import tomlkit
from opensandbox import SandboxSync
from langchain_opensandbox import OpenSandboxBackend
from opensandbox.config.connection_sync import ConnectionConfigSync
from opensandbox.exceptions import SandboxTimeoutException
from config.settings import SANDBOX_PORT_NUMBER, SANDBOX_API_KEY,CONFIG_PATH, SANDBOX_ENABLED, subagent_enabled

CONNECTION_CONFIG = ConnectionConfigSync(
    domain=f"127.0.0.1:{SANDBOX_PORT_NUMBER}",
    protocol="http",
    api_key=SANDBOX_API_KEY,
)

SANDBOX_LOCK = asyncio.Lock()

@cache
def resolve_sandbox_cmd():
    executable = shutil.which("opensandbox-server")
    if executable:
        return [executable]
    local_executable = shutil.which(
        "opensandbox-server",
        path=str(Path(sys.executable).parent),
    )
    if local_executable:
        return [local_executable]
    try:
        module_installed = importlib.util.find_spec("opensandbox_server.cli") is not None
    except (ImportError, ValueError):
        module_installed = False
    if module_installed:
        return [sys.executable, "-m", "opensandbox_server.cli"]
    uvx = shutil.which("uvx")
    if uvx:
        return [uvx, "opensandbox-server"]
    uv = shutil.which("uv")
    if uv:
        return [uv, "tool", "run", "opensandbox-server"]
    pipx = shutil.which("pipx")
    if pipx:
        return [pipx, "run", "opensandbox-server"]
    return None

#save sandbox details with this base class
class SandboxContext(TypedDict):
    sandbox_session: dict[str, Any]

def build_sandbox_config(force=False):
    server_cmd = resolve_sandbox_cmd()
    if server_cmd is None:
        raise RuntimeError("OpenSandbox server command not found")
    config_path = Path(CONFIG_PATH)
    try:
        if force or not config_path.is_file():
            config_cmd = [*server_cmd, "init-config", CONFIG_PATH, "--example", "docker"]
            if force:
                config_cmd.append("--force")
            subprocess.run(
                config_cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        with open(config_path, "r", encoding="utf-8") as f:
            config = tomlkit.load(f)
        config["server"]["port"] = SANDBOX_PORT_NUMBER
        config["server"]["api_key"] = SANDBOX_API_KEY
        with open(config_path, "w", encoding="utf-8") as f:
            tomlkit.dump(config, f)
        config_path.chmod(0o600)
    except Exception as error:
        raise RuntimeError("Error encountered building sandbox config") from error
def check_sandbox_server():
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{SANDBOX_PORT_NUMBER}/health",
            timeout=1,
        ) as res:
            return json.load(res).get("status")=="healthy"
    except Exception:
        return False

def sandbox_available():
    return (
        check_sandbox_server()
        or resolve_sandbox_cmd() is not None
    )

def kill_sandbox_server(process):
    if process is None or process.poll() is not None:
        return
    os.killpg(os.getpgid(process.pid),signal.SIGTERM) if os.name!="nt" else subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True,timeout=10)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()

def start_sandbox_server():
    if check_sandbox_server():
        return None
    build_sandbox_config()
    server_cmd = resolve_sandbox_cmd()
    process=subprocess.Popen([*server_cmd, "--config", CONFIG_PATH],start_new_session=(os.name!="nt"))
    timeout=time.monotonic() +30
    while time.monotonic() < timeout:
        if check_sandbox_server():
            return process
        if process.poll() is not None:
            raise RuntimeError("Sandbox failed to start")
    kill_sandbox_server(process)
    raise RuntimeError("Sandbox failed to start")


@asynccontextmanager
async def sandbox():
    async with SANDBOX_LOCK:
        process=await asyncio.to_thread(start_sandbox_server)
        sandbox=None
        try:
            sandbox = await asyncio.to_thread(SandboxSync.create,
                "python:3.12",
                connection_config=CONNECTION_CONFIG,
            )
            yield OpenSandboxBackend(sandbox=sandbox,timeout=30)
        finally:
            try:
                if sandbox is not None:
                    await asyncio.to_thread(sandbox.destroy)
            finally:
                await asyncio.to_thread(kill_sandbox_server,process)

@tool
async def sandbox_execute(command: str,runtime:ToolRuntime[SandboxContext],offset:int=0,limit:int=1000,timeout:int=30)->str:
    """
    Run a shell command and return a character window of its output.
    Args:
        command: Command to run.
        offset: Character offset into the output.
        limit: Maximum characters to return.
        timeout: Server-side timeout in seconds; 0 disables it.
    Reusing the same command with offset > 0 reads cached output.
    offset=0 reruns the command.
    Returns:
        str: Command output
    """
    if offset<0:
        return "offset must be > or = to 0"
    if limit <= 0:
        return "limit must be > 0"
    limit = min(limit, 10000)
    if timeout < 0:
        return "timeout must be > or = 0"
    session=(runtime.context or {}).get("sandbox_session")
    if not session:
        return "Sandbox backend not available"
    if offset>0 and session["command"]==command:
        output=session["output"]
        exit_code=session["exit_code"]
    else:
        try:
            res=await session["backend"].aexecute(command,timeout=timeout)
        except SandboxTimeoutException:
            if timeout:
                return f"Sandbox command timed out after {timeout} seconds"
            return "Sandbox command timed out"
        except Exception as e:
            return f"Sandbox command failed: {e}"
        output=res.output
        exit_code=res.exit_code
        session["command"]=command
        session["output"]=output
        session["exit_code"]=exit_code
    end = min(offset+limit,len(output))
    window=output[offset:end]
    return (
        f"exit_code={exit_code} "
        f"offset={offset} limit={limit} "
        f"total_characters={len(output)} "
        f"has_more={str(end < len(output)).lower()}\n"
        f"{window}"
    )
async def build_sandbox_agent(model):
    if not subagent_enabled("sandbox_agent", SANDBOX_ENABLED) or not sandbox_available():
        return None
    graph = create_agent(
        model=model,
        name="sandbox_agent",
        tools=[sandbox_execute],
        context_schema=SandboxContext,
        system_prompt="""
        You run shell commands in an isolated Linux sandbox.
        Use sandbox_execute for commands.
        Return a concise summary of the result.
        Files in the sandbox are deleted when the task ends
        """
    )
    async def run(state,config):
        async with sandbox() as backend:
            session={
                "backend":backend,
                "command":None,
                "output":"",
                "exit_code":None,
            }
            return await graph.ainvoke(state,config,context={"sandbox_session":session})
    return CompiledSubAgent(
        name="sandbox_agent",
        description="Runs isolated shell and file tasks in a temporary Linux sandbox.",
        runnable=RunnableLambda(run)
    )
