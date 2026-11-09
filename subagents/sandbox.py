import json
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
import urllib
import signal
import subprocess
import os
import asyncio
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain.tools import ToolRuntime, tool
from langchain.agents import create_agent
import tomlkit
from opensandbox import SandboxSync
from langchain_opensandbox import OpenSandboxBackend
from opensandbox.config.connection_sync import ConnectionConfigSync
from config.settings import SANDBOX_PORT_NUMBER, SANDBOX_API_KEY,CONFIG_PATH

CONNECTION_CONFIG = ConnectionConfigSync(
    domain=f"127.0.0.1:{SANDBOX_PORT_NUMBER}",
    protocol="http",
    api_key=SANDBOX_API_KEY,
)

def build_sandbox_config(force=False):
    config_path = Path(CONFIG_PATH)
    try:
        if force or not config_path.is_file():
            config_cmd = ["uvx","opensandbox-server","init-config",CONFIG_PATH,"--example","docker",]
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

def kill_sandbox_server(process):
    if process is None or process.poll() is None:
        return
    os.killpg(os.getpid(process.pid),signal.SIGTERM) if os.name=="nt" else subprocess.run(["taskkill","/PID",str(process.pid),"/T","/F"],capture_output=True,timeout=10)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()

def start_sandbox_server():
    build_sandbox_config()
    if check_sandbox_server():
        return
    process=subprocess.Popen(["uvx", "opensandbox-server", "--config", CONFIG_PATH])
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

def sandbox_config(config,backend):
    config=dict(config or {})
    configurable = dict(config.get("configurable", {}))
    configurable["sandbox_backend"] = backend
    config["configurable"] = configurable
    return config

@tool
async def sandbox_execute(command: str,runtime:ToolRuntime)->str:
    """Run a shell command inside the sandbox"""
    configurable=(runtime.config or {}).get("configurable")or {}
    backend=configurable.get("sandbox_backend")
    if not backend:
        return "Sandbox backend not available"
    try:
        res=await backend.aexecute(command)
    except Exception as e:
        return f"Sandbox command failed: {e}"
    return f"exit_code={res.exit_code}\n{res.output}".strip()
def build_sandbox_agent(model):
    graph = create_agent(
        model=model,
        name="sandbox_agent",
        tools=[sandbox_execute],
        system_prompt="""
        You run shell commands in an isolated Linux sandbox.
        Use sandbox_execute for commands.
        Return a concise summary of the result.
        Files in the sandbox are deleted when the task ends
        """
    )
