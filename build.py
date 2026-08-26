"""One-time setup for this agent.

Creates the venv and installs dependencies, then delegates shared
infrastructure setup (llama.cpp, embedding model) to the engine.

Idempotent — re-running after a failure picks up where it left off.
Run with the system Python:

    python build.py

Then store your API keys:

    python add_secrets.py
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def fail(message: str) -> None:
    sys.exit(f"\nERROR: {message}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def first_run_setup() -> str:
    """Name the agent on first run, based on the directory name.

    Returns the agent ID (from dashboard.json, possibly just updated).
    """
    dashboard_path = ROOT / "dashboard.json"
    dashboard = json.loads(dashboard_path.read_text())

    if dashboard["id"] != "my-agent":
        return dashboard["id"]

    dir_name = ROOT.name.lower()
    display_name = dir_name.replace("-", " ").replace("_", " ").title()

    # Check for collision with an existing agent
    agent_home = Path.home() / f".{dir_name}"
    if agent_home.exists():
        parent = ROOT.parent
        suffix = 2
        while (parent / f"{dir_name}-{suffix}").exists():
            suffix += 1
        suggestion = f"{dir_name}-{suffix}"
        fail(
            f"~/.{dir_name}/ already exists — another agent is using this name.\n"
            f"Rename this repo's directory and run build.py again:\n\n"
            f"    mv {ROOT} /{parent}/{suggestion}\n"
            f"    cd /{parent}/{suggestion}\n"
            f"    python build.py"
        )

    print(f"Naming this agent: {display_name} (id: {dir_name})")
    confirm = input("Accept? [Y/n] ").strip().lower()
    if confirm == "n":
        dir_name = input("Agent id (lowercase, no spaces): ").strip().lower()
        display_name = input("Display name: ").strip()

        # Check collision again with the manually entered name
        agent_home = Path.home() / f".{dir_name}"
        if agent_home.exists():
            fail(
                f"~/.{dir_name}/ already exists — another agent is using this name.\n"
                f"Choose a different name and run build.py again."
            )

    dashboard["id"] = dir_name
    dashboard["name"] = display_name
    dashboard_path.write_text(json.dumps(dashboard, indent=4) + "\n")

    # Remove upstream funding metadata
    github_dir = ROOT / ".github"
    if github_dir.is_dir():
        shutil.rmtree(github_dir)
        print("  Removed .github/")

    # Update pyproject.toml
    toml_path = ROOT / "pyproject.toml"
    content = toml_path.read_text()
    content = content.replace('name = "my-agent"', f'name = "{dir_name}"')
    toml_path.write_text(content)

    print(f"  Updated dashboard.json and pyproject.toml\n")
    return dir_name


def create_venv() -> None:
    print("\n[1/2] Creating virtual environment and installing dependencies")

    if not venv_python().exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        print(f"    created {VENV}")
    else:
        print(f"    already done — {VENV} exists")

    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", "."],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail("pip install failed — see output above")
    print("    dependencies installed")


def build_infra() -> None:
    print("\n[2/2] Shared inference infrastructure")

    result = subprocess.run(
        [str(venv_python()), "-m", "basic_bot.infrastructure"],
    )
    if result.returncode != 0:
        fail("infrastructure setup failed — see output above")


def main() -> None:
    agent_id = first_run_setup()
    agent_home = Path.home() / f".{agent_id}"

    print(f"{agent_id} — setup")
    agent_home.mkdir(exist_ok=True)
    create_venv()
    build_infra()
    print(
        "\nSetup complete. Store your API keys, then start the agent:\n"
        "\n    python add_secrets.py"
        "\n    python run.py\n"
    )


if __name__ == "__main__":
    main()
