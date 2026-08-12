"""Launch this agent locally.

Ensures llama-server (shared embeddings, port 11444) is running —
starting it from ~/.bountiful/ if it isn't — then starts the Flask UI.
Ctrl+C stops the UI, and stops llama-server only if this process
started it.

Run with any Python — it re-executes itself inside .venv:

    python run.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


# Re-exec inside the venv if we aren't already. Everything above this
# line must be stdlib-only — venv packages aren't importable yet.
if sys.prefix == sys.base_prefix:
    interpreter = _venv_python()
    if not interpreter.exists():
        sys.exit("No .venv found — run 'python build.py' first.")
    os.execv(str(interpreter), [str(interpreter), *sys.argv])

# --- From here on we're inside the venv ---

import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

import keyring
import keyring.errors

from config import FLASK_PORT

AGENT_ID = json.loads((ROOT / "dashboard.json").read_text())["id"]

try:
    api_key = keyring.get_password(AGENT_ID, "anthropic_api_key")
except keyring.errors.KeyringError as e:
    sys.exit(f"Could not read system keyring: {e}\nRun 'python setup_keys.py' first.")

if not api_key:
    sys.exit("No Anthropic API key found — run 'python setup_keys.py' first.")

os.environ["ANTHROPIC_API_KEY"] = api_key

from basic_bot.config import EMBEDDING_PROVIDER, EMBEDDING_URL

BOUNTIFUL_HOME = Path.home() / ".bountiful"
SERVER_BIN = BOUNTIFUL_HOME / "llama.cpp" / "build" / "bin" / "llama-server"
MODEL_FILE = BOUNTIFUL_HOME / "models" / "Qwen3-Embedding-0.6B-Q8_0.gguf"
LLAMA_LOG = BOUNTIFUL_HOME / "llama-server.log"

HEALTH_TIMEOUT = 60  # seconds to wait for llama-server to come up


def _port_from_url(url: str) -> int:
    parsed = urllib.parse.urlsplit(url)
    if parsed.port is None:
        sys.exit(f"EMBEDDING_URL has no port: {url}")
    return parsed.port


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(
            f"http://localhost:{port}/health", timeout=2,
        ) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError):
        return False


def ensure_llama_server() -> subprocess.Popen | None:
    """Start llama-server unless one is already running.

    Returns the process if this run started it (caller tears it down),
    or None if an existing server is being reused (leave it alone).
    """
    port = _port_from_url(EMBEDDING_URL)

    if _port_in_use(port):
        if _healthy(port):
            print(f"llama-server already running on port {port} — reusing it")
            return None
        sys.exit(
            f"Port {port} is in use but not responding as llama-server.\n"
            f"Something else may be running there — stop it, or set\n"
            f"EMBEDDING_URL in your environment to use a different port."
        )

    if not SERVER_BIN.exists() or not MODEL_FILE.exists():
        sys.exit(
            "llama-server or the embedding model is missing from ~/.bountiful/.\n"
            "Run 'python build.py' first."
        )

    log = open(LLAMA_LOG, "w")
    process = subprocess.Popen(
        [
            str(SERVER_BIN),
            "-m", str(MODEL_FILE),
            "--embeddings",
            "--port", str(port),
            "--ubatch-size", "8192",    # max tokens per embedding input
            "--ctx-size", "8192",       # matches ubatch; model max is 32768
            "--parallel", "1",          # single slot; one client
        ],
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    print(f"llama-server starting on port {port} (log: {LLAMA_LOG})")

    deadline = time.monotonic() + HEALTH_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            sys.exit(f"llama-server exited during startup — check {LLAMA_LOG}")
        if _healthy(port):
            print("llama-server ready — embeddings available")
            return process
        time.sleep(0.5)

    process.terminate()
    sys.exit(f"llama-server did not become ready in {HEALTH_TIMEOUT}s — check {LLAMA_LOG}")


def main() -> None:
    llama = ensure_llama_server() if EMBEDDING_PROVIDER == "local" else None

    try:
        from basic_ui.server import create_local_app
        app = create_local_app(ROOT)
        # use_reloader=False: the reloader re-runs this script in a child
        # process, which would spawn a second llama-server.
        app.run(port=FLASK_PORT, debug=True, use_reloader=False)
    finally:
        if llama is not None:
            llama.terminate()
            try:
                llama.wait(timeout=10)
            except subprocess.TimeoutExpired:
                llama.kill()
            print("llama-server stopped")


if __name__ == "__main__":
    main()
