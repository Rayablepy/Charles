import asyncio
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

import click

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VENV_BIN = Path(sys.executable).parent
PYTHON = sys.executable
LANGGRAPH = VENV_BIN / ("langgraph.exe" if os.name == "nt" else "langgraph")
FRONTEND = ROOT / "interfaces" / "frontend"

CONNECT_TIMEOUT = 1.0
HEALTH_TIMEOUT = 1.0
BACKEND_MAX_WAIT = 60.0
KILL_MAX_WAIT = 5.0
TASKKILL_TIMEOUT = 15.0


def is_up(port: int) -> bool:
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=CONNECT_TIMEOUT):
                return True
        except OSError:
            continue
    return False


def wait_up(port: int, max_wait: float) -> bool:
    url = f"http://127.0.0.1:{port}/ok"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def spawn(name: str, cwd: Path, argv: list, port: int, extra_env: dict | None = None):
    if is_up(port):
        click.echo(f"{name} already running on :{port} (reused)")
        return None
    click.echo(f"starting {name} on :{port} ...")
    env = os.environ.copy()
    env.update(extra_env or {})
    return subprocess.Popen(argv, cwd=str(cwd), env=env)


def kill(proc) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            timeout=TASKKILL_TIMEOUT,
        )
    else:
        proc.terminate()
    try:
        proc.wait(timeout=KILL_MAX_WAIT)
    except subprocess.TimeoutExpired:
        pass


@click.group()
def main():
    pass


@main.command()
def cli():
    import interfaces.cli
    asyncio.run(interfaces.cli.main())


@main.command()
@click.option("--backend-port", default=2024, show_default=True, help="langgraph dev server port")
@click.option("--ingest-port", default=2030, show_default=True, help="document ingest API port")
@click.option("--vite-port", default=5173, show_default=True, help="vite dev server port")
@click.option("--backend-wait", default=BACKEND_MAX_WAIT, show_default=True,
              help="max seconds to wait for a cold backend to become ready")
@click.option("--no-open", is_flag=True, help="do not open the browser")
def web(backend_port, ingest_port, vite_port, backend_wait, no_open):
    procs = []

    backend = spawn(
        "langgraph backend",
        ROOT,
        [PYTHON, str(LANGGRAPH), "dev", "--host", "127.0.0.1",
         "--port", str(backend_port), "--no-browser", "--allow-blocking"],
        backend_port,
    )
    if backend:
        procs.append(backend)
        if not wait_up(backend_port, backend_wait):
            click.echo(f"warning: backend not ready within {backend_wait:.0f}s")

    ingest = spawn(
        "ingest api",
        ROOT,
        [PYTHON, "-m", "interfaces.ingest"],
        ingest_port,
        {"INGEST_API_HOST": "127.0.0.1", "INGEST_API_PORT": str(ingest_port)},
    )
    if ingest:
        procs.append(ingest)

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        vite = spawn(
            "vite frontend",
            FRONTEND,
            [npm, "run", "dev", "--", "--host", "127.0.0.1",
             "--port", str(vite_port), "--strictPort"],
            vite_port,
        )
        if vite:
            procs.append(vite)
    else:
        click.echo("npm not found; skipping frontend")

    url = f"http://localhost:{vite_port}/"
    if not no_open:
        webbrowser.open(url)
    click.echo(f"{url}  (Ctrl+C to stop)")

    if not procs:
        click.echo("nothing to manage - all components already running")
        return

    try:
        while any(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nshutting down ...")
    finally:
        for p in procs:
            kill(p)
        click.echo("stopped")


if __name__ == "__main__":
    main()