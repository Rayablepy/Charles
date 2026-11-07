import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from opensandbox import SandboxSync
from langchain_opensandbox import OpenSandboxBackend
from opensandbox.config.connection_sync import ConnectionConfigSync
from config.settings import SANDBOX_PORT_NUMBER

CONNECTIONCONFIG = ConnectionConfigSync(
    domain=f"127.0.0.1:{SANDBOX_PORT_NUMBER}",
    protocol="http",
)
def ensure_sandbox():
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