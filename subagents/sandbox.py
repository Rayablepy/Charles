import sys
from pathlib import Path
import subprocess
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

def ensure_sandbox():
    try:
        build_sandbox_config()
        subprocess.Popen(["uvx","opensandbox-server", "--config",CONFIG_PATH])
    except:
        raise RuntimeError("Sandbox failed to start")
    try:
        sandbox=SandboxSync.create("python:3.12",connection_config=CONNECTION_CONFIG)
        backend=OpenSandboxBackend(sandbox=sandbox,timeout=100)
    except:
        raise RuntimeError("Sandbox failed to start")
    return
if __name__ == "__main__":
    ensure_sandbox()
