import sys
from pathlib import Path
import subprocess
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tomlkit
from opensandbox import SandboxSync
from langchain_opensandbox import OpenSandboxBackend
from opensandbox.config.connection_sync import ConnectionConfigSync
from config.settings import SANDBOX_PORT_NUMBER, SANDBOX_API_KEY

CONNECTIONCONFIG = ConnectionConfigSync(
    domain=f"127.0.0.1:{SANDBOX_PORT_NUMBER}",
    protocol="http",
    api_key=SANDBOX_API_KEY,
)
def build_sandbox_config():
    try:
        config_path=str(Path.home() / ".sandbox.toml")
        subprocess.run(["uvx","opensandbox-server", "init-config",config_path, "--example","docker"])
        with open(config_path,"r",encoding="utf-8") as f:
            config=tomlkit.load(f)
        config["server"]["port"]=SANDBOX_PORT_NUMBER
        config["server"]["api_key"]=SANDBOX_API_KEY
        with open(config_path, "w", encoding="utf-8") as f:
            tomlkit.dump(config, f)
    except:
        raise RuntimeError("Error encountered building sandbox config")

def ensure_sandbox():
    try:
        build_sandbox_config()
        subprocess.Popen(["uvx","opensandbox-server"])
    except:
        raise RuntimeError("Sandbox failed to start")
    try:
        sandbox=SandboxSync.create("python:3.12",connection_config=CONNECTIONCONFIG)
        print('Sandbox started')
        backend=OpenSandboxBackend(sandbox=sandbox,timeout=100)
        res=backend.execute("echo hello")
        print(res.output)
        sandbox.destroy()
        print('Sandbox stopped')
    except:
        raise RuntimeError("Sandbox failed to start")
    return
if __name__ == "__main__":
    ensure_sandbox()
