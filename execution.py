import argparse
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

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

MODE = sys.argv[1] if len(sys.argv) > 1 else ""

VENV_PY = Path(sys.executable)
VENV_BIN = VENV_PY.parent
LANGGRAPH_CLI = VENV_BIN / ("langgraph.exe" if os.name == "nt" else "langgraph")


def is_up(port: int, timeout: float = 0.6) -> bool:
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def wait_up(port: int, seconds: float) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/ok", timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    print(f"[web] warning: backend on :{port} did not answer within {seconds:.0f}s")
    return False


def spawn(name: str, cwd: Path, argv: list, port: int, extra_env: dict | None = None):
    if is_up(port):
        print(f"[web] {name} already running on :{port} (reused)")
        return None
    env = dict(os.environ)
    env.update(extra_env or {})
    print(f"[web] starting {name} on :{port} ...")
    return subprocess.Popen(argv, cwd=str(cwd), env=env)


def kill(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=15)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def web(argv: list):
    parser = argparse.ArgumentParser(prog="execution.py web")
    parser.add_argument("--backend-port", type=int, default=2024)
    parser.add_argument("--ingest-port", type=int, default=2030)
    parser.add_argument("--vite-port", type=int, default=5173)
    args = parser.parse_args(argv)

    procs = []
    backend = spawn(
        "langgraph backend",
        ROOT,
        [str(VENV_PY), str(LANGGRAPH_CLI), "dev", "--host", "127.0.0.1",
         "--port", str(args.backend_port), "--no-browser"],
        args.backend_port,
    )
    if backend:
        procs.append(backend)
        wait_up(args.backend_port, 60)

    ingest = spawn(
        "ingest api",
        ROOT,
        [str(VENV_PY), "-m", "interfaces.ingest"],
        args.ingest_port,
        {"INGEST_API_HOST": "127.0.0.1", "INGEST_API_PORT": str(args.ingest_port)},
    )
    if ingest:
        procs.append(ingest)

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if npm:
        vite = spawn(
            "vite frontend",
            ROOT / "interfaces" / "frontend",
            [npm, "run", "dev", "--", "--host", "127.0.0.1",
             "--port", str(args.vite_port), "--strictPort"],
            args.vite_port,
        )
        if vite:
            procs.append(vite)
    else:
        print("[web] npm not found; skipping frontend")

    url = f"http://localhost:{args.vite_port}/"
    print(f"[web] {url}  (Ctrl+C to stop)")
    webbrowser.open(url)

    if not procs:
        print("[web] nothing to manage - all components already running")
        return 0

    try:
        while any(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[web] shutting down ...")
    finally:
        for p in procs:
            kill(p)
        print("[web] stopped")
    return 0


USAGE = """\
usage:
  python execution.py cli             console agent loop
  python execution.py web             full web app (backend + ingest + vite)
    --backend-port N    langgraph dev port   (default 2024)
    --ingest-port N     ingest api port      (default 2030)
    --vite-port N       vite dev port        (default 5173)
"""


if MODE == "cli":
    from interfaces.cli import main
    asyncio.run(main())
elif MODE == "web":
    sys.exit(web(sys.argv[2:]))
elif MODE in ("-h", "--help", "help"):
    print(USAGE)
    sys.exit(0)
else:
    print(USAGE)
    sys.exit(2)