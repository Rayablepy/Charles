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

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import (
    DEFAULT_BACKEND_PORT,
    DEFAULT_INGEST_PORT,
    DEFAULT_VITE_PORT,
    ELECTRON_BIN,
    FRONTEND_DIR,
    LANGGRAPH_BIN,
    POLL_INTERVAL,
    PROBE_TIMEOUT,
    PYTHON_BIN,
    REPO_ROOT,
    SHUTDOWN_WAIT,
    STARTUP_WAIT,
)


def is_up(port: int) -> bool:
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=PROBE_TIMEOUT):
                return True
        except OSError:
            continue
    return False


def wait_up(port: int, max_wait: float) -> bool:
    url = f"http://127.0.0.1:{port}/ok"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=PROBE_TIMEOUT):
                return True
        except Exception:
            time.sleep(POLL_INTERVAL)
    return False

def wait_port(port: int, max_wait: float) -> bool:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        if is_up(port):
            return True
        time.sleep(POLL_INTERVAL)
    return False

def electron_path() -> Path | None:
    return ELECTRON_BIN if ELECTRON_BIN.exists() else None

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
            timeout=SHUTDOWN_WAIT,
        )
    else:
        proc.terminate()
    try:
        proc.wait(timeout=SHUTDOWN_WAIT)
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
@click.option("--backend-port", default=DEFAULT_BACKEND_PORT, show_default=True, help="langgraph dev server port")
@click.option("--ingest-port", default=DEFAULT_INGEST_PORT, show_default=True, help="document ingest API port")
@click.option("--vite-port", default=DEFAULT_VITE_PORT, show_default=True, help="vite dev server port")
@click.option("--backend-wait", default=STARTUP_WAIT, show_default=True,
              help="max seconds to wait for a cold backend to become ready")
@click.option("--no-open", is_flag=True, help="do not open Electron or a browser")
@click.option("--browser", is_flag=True, help="open the system browser instead of Electron")
def web(backend_port, ingest_port, vite_port, backend_wait, no_open, browser):
    procs = []

    backend = spawn(
        "langgraph backend",
        REPO_ROOT,
        [PYTHON_BIN, str(LANGGRAPH_BIN), "dev", "--host", "127.0.0.1",
         "--port", str(backend_port), "--no-browser", "--allow-blocking"],
        backend_port,
    )
    if backend:
        procs.append(backend)
        if not wait_up(backend_port, backend_wait):
            click.echo(f"warning: backend not ready within {backend_wait:.0f}s")

    ingest = spawn(
        "ingest api",
        REPO_ROOT,
        [PYTHON_BIN, "-m", "interfaces.ingest"],
        ingest_port,
        {"INGEST_API_HOST": "127.0.0.1", "INGEST_API_PORT": str(ingest_port)},
    )
    if ingest:
        procs.append(ingest)

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        vite = spawn(
            "vite frontend",
            FRONTEND_DIR,
            [npm, "run", "dev", "--", "--host", "127.0.0.1",
             "--port", str(vite_port), "--strictPort"],
            vite_port,
        )
        if vite:
            procs.append(vite)
            if not wait_port(vite_port, STARTUP_WAIT):
                click.echo(f"warning: vite not ready within {STARTUP_WAIT:.0f}s")
    else:
        click.echo("npm not found; skipping frontend")

    url = f"http://127.0.0.1:{vite_port}/"
    electron_proc = None
    if not no_open:
        wrapper = None if browser else electron_path()
        if wrapper is not None:
            click.echo(f"starting electron wrapper -> {url} ...")
            env = os.environ.copy()
            env["VITE_DEV_SERVER_URL"] = url
            electron_proc = subprocess.Popen(
                [str(wrapper), "."], cwd=str(FRONTEND_DIR), env=env
            )
            procs.append(electron_proc)
        else:
            if not browser:
                click.echo("electron not found; opening browser instead")
            webbrowser.open(url)
    click.echo(f"{url}  (Ctrl+C to stop)")

    if not procs:
        click.echo("nothing to manage - all components already running")
        return

    try:
        if electron_proc is not None:
            electron_proc.wait()
            click.echo("\nelectron closed; shutting down ...")
        else:
            while any(p.poll() is None for p in procs):
                time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        click.echo("\nshutting down ...")
    finally:
        for p in procs:
            kill(p)
        click.echo("stopped")


if __name__ == "__main__":
    main()
