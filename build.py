"""One-time setup for this agent.

Creates the venv and installs dependencies, then ensures the shared
Bountiful inference infrastructure exists at ~/.bountiful/ — llama.cpp
(built from source, CPU) and the embedding model. The first agent
built on a machine creates the infrastructure; every later agent
finds it and skips.

Idempotent — re-running after a failure picks up where it left off.
Run with the system Python:

    python build.py

Then store your API keys:

    python setup_keys.py
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"

AGENT_ID = json.loads((ROOT / "dashboard.json").read_text())["id"]
AGENT_HOME = Path.home() / f".{AGENT_ID}"

# Shared Bountiful infrastructure — one copy serves every agent
BOUNTIFUL_HOME = Path.home() / ".bountiful"
LLAMA_DIR = BOUNTIFUL_HOME / "llama.cpp"
LLAMA_REPO = "https://github.com/ggml-org/llama.cpp.git"
SERVER_BIN = LLAMA_DIR / "build" / "bin" / "llama-server"

MODELS_DIR = BOUNTIFUL_HOME / "models"
MODEL_NAME = "Qwen3-Embedding-0.6B-Q8_0.gguf"
MODEL_FILE = MODELS_DIR / MODEL_NAME
MODEL_URL = (
    "https://huggingface.co/CablepunkPress/Qwen3-Embedding-0.6B-GGUF"
    f"/resolve/main/{MODEL_NAME}"
)

TOTAL_STEPS = 4


def step(n: int, message: str) -> None:
    print(f"\n[{n}/{TOTAL_STEPS}] {message}")


def skip(message: str) -> None:
    print(f"    already done — {message}")


def fail(message: str) -> None:
    sys.exit(f"\nERROR: {message}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def check_prerequisites() -> None:
    step(1, "Checking prerequisites")

    missing = []
    if shutil.which("git") is None:
        missing.append("git")
    if shutil.which("cmake") is None:
        missing.append("cmake")
    if not any(shutil.which(c) for c in ("c++", "g++", "clang++", "cc")):
        missing.append("a C++ compiler (g++ or clang++)")

    if missing:
        fail(
            "Missing required tools: " + ", ".join(missing) + "\n"
            "Install them with your system package manager and re-run.\n"
            "  Arch:           sudo pacman -S git cmake gcc\n"
            "  Debian/Ubuntu:  sudo apt install git cmake build-essential\n"
            "  Fedora:         sudo dnf install git cmake gcc-c++\n"
            "  macOS:          xcode-select --install && brew install cmake"
        )
    print("    git, cmake, and a C++ compiler found")


def create_venv() -> None:
    step(2, "Creating virtual environment and installing dependencies")

    if not venv_python().exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        print(f"    created {VENV}")
    else:
        skip(f"{VENV} exists")

    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "."],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail("pip install failed — see output above")
    print("    dependencies installed")


def install_tool_dependencies() -> None:
    """Install pip dependencies declared in tools/*/tool.json."""
    tools_dir = ROOT / "tools"
    if not tools_dir.is_dir():
        return

    all_deps: list[str] = []
    for manifest_path in tools_dir.glob("*/tool.json"):
        manifest = json.loads(manifest_path.read_text())
        all_deps.extend(manifest.get("dependencies", []))

    if not all_deps:
        return

    unique = sorted(set(all_deps))
    print(f"    installing tool dependencies: {', '.join(unique)}")
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install"] + unique,
    )
    if result.returncode != 0:
        fail("tool dependency install failed — see output above")


def build_llama_cpp() -> None:
    step(3, "Shared inference infrastructure: llama.cpp (CPU)")

    if SERVER_BIN.exists():
        skip(f"{SERVER_BIN} exists")
        return

    BOUNTIFUL_HOME.mkdir(parents=True, exist_ok=True)

    if not (LLAMA_DIR / "CMakeLists.txt").exists():
        result = subprocess.run(
            ["git", "clone", "--depth", "1", LLAMA_REPO, str(LLAMA_DIR)],
        )
        if result.returncode != 0:
            fail("git clone of llama.cpp failed — see output above")

    print("    compiling llama-server — this takes a few minutes...")
    configure = subprocess.run(["cmake", "-B", "build"], cwd=LLAMA_DIR)
    if configure.returncode != 0:
        fail("cmake configure failed — see output above")

    build = subprocess.run(
        [
            "cmake", "--build", "build",
            "--config", "Release",
            "--target", "llama-server",
            "-j", str(os.cpu_count() or 4),
        ],
        cwd=LLAMA_DIR,
    )
    if build.returncode != 0 or not SERVER_BIN.exists():
        fail("llama.cpp build failed — see output above")
    print(f"    built {SERVER_BIN}")


def download_model() -> None:
    step(4, f"Shared inference infrastructure: embedding model ({MODEL_NAME}, ~639 MB)")

    if MODEL_FILE.exists():
        skip(f"{MODEL_FILE} exists")
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    partial = MODEL_FILE.with_suffix(".partial")

    def report(count: int, block_size: int, total: int) -> None:
        if total > 0:
            done = min(count * block_size, total)
            percent = done * 100 // total
            mb = done // (1024 * 1024)
            print(f"\r    {percent}% ({mb} MB)", end="", flush=True)

    try:
        urllib.request.urlretrieve(MODEL_URL, partial, reporthook=report)
    except Exception as e:
        if partial.exists():
            partial.unlink()
        fail(f"model download failed: {e}\nURL: {MODEL_URL}")

    partial.rename(MODEL_FILE)
    print(f"\n    saved to {MODEL_FILE}")


def main() -> None:
    print(f"{AGENT_ID} — setup")
    AGENT_HOME.mkdir(exist_ok=True)
    check_prerequisites()
    create_venv()
    install_tool_dependencies()
    build_llama_cpp()
    download_model()
    print(
        "\nSetup complete. Store your API keys, then start the agent:\n"
        "\n    python setup_keys.py"
        "\n    python run.py\n"
    )


if __name__ == "__main__":
    main()
