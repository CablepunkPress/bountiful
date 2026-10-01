"""One-time setup for this agent.

Creates the venv and installs dependencies, then delegates shared
infrastructure setup (llama.cpp, embedding model, summary model, chat model)
to the engine in 'basic-bot' repo.

Idempotent — re-running after a failure picks up where it left off.
Re-running after a system Python upgrade rebuilds the venv for the
new interpreter. The agent's memory and identity are never touched.

Run with the system Python:

    python3 build.py
"""

from __future__ import annotations

import sys

# This check must stay above everything else, written so that older
# versions of Python can read it. Keep it in step with requires-python
# in pyproject.toml.
if sys.version_info < (3, 14):
    sys.exit(
        f"Bountiful needs Python 3.14 or newer. This is Python "
        f"{sys.version_info.major}.{sys.version_info.minor}, "
        f"from {sys.executable}.\n"
        "On a Mac, follow 'Prepare your Mac' in the README, "
        "then run: python3 build.py"
    )

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"

TEMPLATE_ID = "my-agent"
RESERVED_IDS = {
    "bountiful": "it is reserved for shared infrastructure (~/.bountiful/)",
    TEMPLATE_ID: "it is the template's placeholder name",
}
VALID_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")


def fail(message: str) -> None:
    sys.exit(f"\nERROR: {message}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def venv_version() -> tuple[int, int] | None:
    """The major.minor Python version the venv was built with.

    Every venv records its interpreter version in pyvenv.cfg. Returns
    None if the file is missing or unreadable.
    """
    cfg = VENV / "pyvenv.cfg"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() in ("version", "version_info"):
            try:
                major, minor = value.strip().split(".")[:2]
                return int(major), int(minor)
            except ValueError:
                return None
    return None


def describe(version: tuple[int, int] | None) -> str:
    if version is None:
        return "an unknown version"
    return f"{version[0]}.{version[1]}"


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

def id_from(name: str) -> str:
    """Turn a name like 'My Test' into an id like 'my-test'."""
    return re.sub(r"\s+", "-", name.strip().lower())


def id_problem(agent_id: str) -> str | None:
    """Why an agent id can't be used, or None if it's fine.

    The id becomes a directory name (~/.{id}/), a keyring entry, and
    a log prefix, so it must be simple, unreserved, and unused.
    """
    if not agent_id:
        return "The agent id can't be empty."
    if agent_id in RESERVED_IDS:
        return f"'{agent_id}' can't be used because {RESERVED_IDS[agent_id]}."
    if not VALID_ID.fullmatch(agent_id):
        return (
            f"'{agent_id}' can't be used. Use lowercase letters, numbers, "
            "hyphens, and underscores, starting with a letter or number."
        )
    if (Path.home() / f".{agent_id}").exists():
        return f"~/.{agent_id}/ already exists — another agent is using this name."
    return None


def ask_agent_id() -> str:
    """Prompt until the user enters a usable agent id."""
    while True:
        agent_id = id_from(input("Agent id (lowercase, no spaces): "))
        problem = id_problem(agent_id)
        if problem is None:
            return agent_id
        print(f"  {problem}")


def display_name_for(agent_id: str) -> str:
    """Turn an id like 'my-test' into a display name like 'My Test'."""
    return agent_id.replace("-", " ").replace("_", " ").title()


def first_run_setup() -> str:
    """Name the agent on first run, based on the directory name.

    Returns the agent ID (from dashboard.json, possibly just updated).
    """
    dashboard_path = ROOT / "dashboard.json"
    dashboard = json.loads(dashboard_path.read_text())

    if dashboard["id"] != TEMPLATE_ID:
        return dashboard["id"]

    # Propose the directory's name; ask for an id if it can't be used
    agent_id = id_from(ROOT.name)
    problem = id_problem(agent_id)
    if problem is not None:
        print(f"This directory's name can't become the agent's id. {problem}")
        agent_id = ask_agent_id()

    display_name = display_name_for(agent_id)

    print(f"Naming this agent: {display_name} (id: {agent_id})")
    confirm = input("Accept? [Y/n] ").strip().lower()
    if confirm == "n":
        agent_id = ask_agent_id()
        default_name = display_name_for(agent_id)
        display_name = input(f"Display name [{default_name}]: ").strip() or default_name

    dashboard["id"] = agent_id
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
    content = content.replace(f'name = "{TEMPLATE_ID}"', f'name = "{agent_id}"')
    toml_path.write_text(content)

    print("  Updated dashboard.json and pyproject.toml\n")
    return agent_id


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def install_tool_dependencies() -> None:
    """Reinstall dependencies for every tool group in tools/.

    Tool groups live in the agent directory, but their dependencies
    live in the venv. A rebuilt venv starts empty, so the build
    restores what each installed group declares in its tool.json.
    pip skips anything already satisfied.
    """
    tools_dir = ROOT / "tools"
    if not tools_dir.is_dir():
        return

    deps: set[str] = set()
    for manifest_path in sorted(tools_dir.glob("*/tool.json")):
        manifest = json.loads(manifest_path.read_text())
        deps.update(manifest.get("dependencies", []))

    if not deps:
        return

    print(f"    tool dependencies: {', '.join(sorted(deps))}")
    result = subprocess.run(
        [str(venv_python()), "-m", "pip", "install", *sorted(deps)],
    )
    if result.returncode != 0:
        fail("tool dependency install failed — see output above")


def create_venv() -> None:
    print("\n[1/2] Creating virtual environment and installing dependencies")

    # A venv borrows the system interpreter. If the system Python has
    # moved to a new minor version since the venv was built, the venv
    # is stale and cannot be repaired in place, so it is rebuilt.
    # Patch releases (3.14.6 to 3.14.7) are compatible.
    if VENV.exists():
        built = venv_version()
        running = (sys.version_info.major, sys.version_info.minor)
        if built != running:
            print(
                f"    venv was built with Python {describe(built)}, "
                f"now running {describe(running)} — rebuilding"
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

    install_tool_dependencies()
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
        "\nSetup complete. Start your agent:\n"
        "\n    python3 run.py\n"
    )


if __name__ == "__main__":
    main()
