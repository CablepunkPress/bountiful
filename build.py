"""One-time setup for this agent.

Creates the venv and installs dependencies, then delegates shared
infrastructure setup (llama.cpp, embedding model, summary model, chat model) 
to the engine in 'basic-bot' repo.

Idempotent — re-running after a failure picks up where it left off.
Re-running after a system Python upgrade rebuilds the venv for the
new interpreter. The agent's memory and identity are never touched.

Run with the system Python:

    python build.py
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


def venv_python_version() -> tuple[int, int] | None:
    """Read the major.minor Python version the venv was built with.

    Every venv records its interpreter version in pyvenv.cfg. Returns
    None if the file is missing or unreadable, which is treated the
    same as a mismatch.
    """
    cfg = VENV / "pyvenv.cfg"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() in ("version", "version_info"):
            parts = value.strip().split(".")
            try:
                return int(parts[0]), int(parts[1])
            except (IndexError, ValueError):
                return None
    return None


def first_run_setup() -> str:
    """Name the agent on first run, based on the directory name.

    Returns the agent ID (from dashboard.json, possibly just updated).
    """
    dashboard_path = ROOT / "dashboard.json"
    dashboard = json.loads(dashboard_path.read_text())

    if dashboard["id"] != "my-agent":
        return dashboard["id"]

    dir_name = ROOT.name.lower()

    # "bountiful" is reserved for shared infrastructure (~/.bountiful/)
    if dir_name == "bountiful":
        print("'bountiful' is reserved for shared infrastructure.")
        dir_name = input("Choose an agent id (lowercase, no spaces): ").strip().lower()

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
            f"    mv {ROOT} {parent}/{suggestion}\n"
            f"    cd {parent}/{suggestion}\n"
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

    # A venv borrows the system interpreter. If the system Python has
    # moved to a new minor version since the venv was built, the venv
    # is stale and must be rebuilt. Patch releases (3.14.6 → 3.14.7)
    # are compatible and do not trigger a rebuild.
    if VENV.exists():
        built_with = venv_python_version()
        running = (sys.version_info.major, sys.version_info.minor)
        if built_with != running:
            was = f"{built_with[0]}.{built_with[1]}" if built_with else "an unknown version"
            print(
                f"    venv was built with Python {was}, "
                f"now running {running[0]}.{running[1]} — rebuilding"
            )
            shutil.rmtree(VENV)

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
        [str(venv_python()), "-m", "basic_bot"],
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
        "\nSetup complete. Start the agent:\n"
        "\n    python run.py\n"
    )


if __name__ == "__main__":
    main()
