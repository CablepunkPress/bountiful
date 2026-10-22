"""Build Bountiful on this machine.

Creates the virtual environment and installs Bountiful's packages into
it, then hands over to the engine, which builds llama.cpp and
downloads the AI models into ~/.bountiful, shared by every agent.

Installing Bountiful installs the bountiful command, the way
installing the Google Cloud SDK installs gcloud. Agents are created
and started with it: 'bountiful new', then 'bountiful jeden'. Each
agent lives in its own folder outside this one, so nothing here is
personal.

Idempotent: re-running after a failure picks up where it left off.
Re-running after a system Python upgrade rebuilds the environment for
the new interpreter. No agent's files are ever touched.

Run with the system Python:

    python3 build.py

Options are passed to the engine's build: 'python3 build.py --models'
asks again about every optional chat model.
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
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"

# Where the bountiful command is linked: the usual folder for a user's
# own commands on macOS and Linux.
USER_BIN = Path.home() / ".local" / "bin"
LINK = USER_BIN / "bountiful"

# Bountiful's shared folder, as in basic_bot/paths.py. This file runs
# before the engine is installed, so it can't import it. install.json
# remembers that the PATH question was asked; agents.json is the
# engine's list of agents.
BOUNTIFUL_HOME = Path.home() / ".bountiful"
INSTALL_RECORD = BOUNTIFUL_HOME / "install.json"
AGENTS_REGISTRY = BOUNTIFUL_HOME / "agents.json"

# The one line added to a shell's startup file, at the end of the PATH
# so it never takes precedence over a command the user already has.
PATH_LINE = 'export PATH="$PATH:$HOME/.local/bin"'


def fail(message: str) -> None:
    sys.exit(f"\nERROR: {message}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def venv_command() -> Path:
    """The bountiful command pip installs into the environment."""
    return VENV / "bin" / "bountiful"


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
# This clone
# ---------------------------------------------------------------------------

def disable_push() -> None:
    """Make this clone pull-only, once.

    Updates come from pulling Bountiful's releases, and nothing in
    this folder is personal, so there's never a reason to push from
    it. Pushing is disabled the first time only, and recorded, so a
    developer who turns it back on isn't overruled by later builds.
    """
    if not (ROOT / ".git").exists() or shutil.which("git") is None:
        return

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True,
        )

    if git("config", "--get", "bountiful.pushDisabled").returncode == 0:
        return
    if git("remote", "get-url", "origin").returncode != 0:
        return

    git("remote", "set-url", "--push", "origin", "no-push")
    git("config", "bountiful.pushDisabled", "true")
    print(
        "    made this clone pull-only, since updates come from Bountiful's "
        "releases\n"
        "      (to undo: git remote set-url --push origin <url>)"
    )


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def create_venv() -> None:
    print("\n[1/2] Python environment and Bountiful's packages")

    # A venv borrows the system interpreter. If the system Python has
    # moved to a new minor version since the venv was built, the venv
    # is stale and cannot be repaired in place, so it is rebuilt.
    # Patch releases (3.14.6 to 3.14.7) are compatible.
    if VENV.exists():
        built = venv_version()
        running = (sys.version_info.major, sys.version_info.minor)
        if built != running:
            print(
                f"    the environment was built with Python {describe(built)}, "
                f"now running {describe(running)} — rebuilding it"
            )
            shutil.rmtree(VENV)

    if not venv_python().exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
        print(f"    created a virtual environment in {VENV}")
    else:
        print(f"    using the existing virtual environment in {VENV}")

    print("    installing basic-bot and basic-ui from GitHub")
    result = subprocess.run(
        [
            str(venv_python()), "-m", "pip", "install", "--quiet",
            "--disable-pip-version-check", ".",
        ],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail(
            "installing packages failed — see output above.\n\n"
            "Check your connection, then run 'python3 build.py' again."
        )
    print("    packages installed")


def build_infra(options: list[str]) -> None:
    print("\n[2/2] llama.cpp and AI models, shared by every agent in ~/.bountiful/")

    # Options such as --models belong to the engine, so they're passed
    # along unread. New options then never need a change here.
    result = subprocess.run(
        [str(venv_python()), "-m", "basic_bot", *options],
    )
    if result.returncode != 0:
        # basic_bot has already explained what failed and what to do.
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# The bountiful command
# ---------------------------------------------------------------------------

def link_command() -> None:
    """Link ~/.local/bin/bountiful to this clone's command.

    This is part of installing Bountiful, so it happens on every build.
    A link that already points elsewhere is left alone.
    """
    if LINK.is_symlink() and LINK.resolve() == venv_command().resolve():
        return
    if LINK.exists() or LINK.is_symlink():
        print(
            f"\n    {LINK} already exists and isn't this clone's command, so it "
            f"was left alone.\n    Remove it, then build again, to use this one."
        )
        return
    USER_BIN.mkdir(parents=True, exist_ok=True)
    LINK.symlink_to(venv_command())
    print(f"\n    installed the bountiful command in {USER_BIN}")
    print(f"      (to remove it: rm {LINK})")


def on_path(folder: Path) -> bool:
    return any(
        Path(p).expanduser().resolve() == folder.resolve()
        for p in os.environ.get("PATH", "").split(os.pathsep) if p
    )


def startup_file() -> Path | None:
    """The shell startup file to add the PATH line to, if known."""
    shell = Path(os.environ.get("SHELL", "")).name
    if shell == "zsh":
        return Path.home() / ".zshrc"
    if shell == "bash":
        # On a Mac, Terminal opens login shells, which read .bash_profile
        name = ".bash_profile" if sys.platform == "darwin" else ".bashrc"
        return Path.home() / name
    return None


def _install_record() -> dict:
    try:
        return json.loads(INSTALL_RECORD.read_text())
    except (OSError, ValueError):
        return {}


def offer_path() -> None:
    """Offer, once, to put ~/.local/bin on the PATH.

    The line goes in the shell's startup file only if the user says
    yes. Either way, the question isn't asked again.
    """
    if on_path(USER_BIN):
        return

    record = _install_record()
    rc = startup_file()
    already_added = rc is not None and rc.exists() and PATH_LINE in rc.read_text()
    asked = record.get("path_offered", False)

    if already_added:
        print(
            "\n    Open a new terminal so it finds the bountiful command."
        )
        return

    if asked or rc is None or not sys.stdin.isatty():
        where = f"to {_short(rc)}" if rc else "to your shell's startup file"
        print(
            f"\n    {_short(USER_BIN)} isn't on your PATH, so terminals won't "
            f"find the bountiful command.\n    To fix that, add this line "
            f"{where}, then open a new terminal:\n\n"
            f"        {PATH_LINE}"
        )
        return

    print(
        f"\n    The bountiful command is installed in {_short(USER_BIN)}, "
        f"which isn't on your PATH yet."
    )
    print(f"    This line would let every new terminal find it:\n\n        {PATH_LINE}\n")
    try:
        answer = input(f"    Add it to {_short(rc)}? [Y/n] ").strip().lower()
    except EOFError:
        answer = "n"

    record["path_offered"] = True
    BOUNTIFUL_HOME.mkdir(parents=True, exist_ok=True)
    INSTALL_RECORD.write_text(json.dumps(record, indent=2) + "\n")

    if answer in ("", "y", "yes"):
        with open(rc, "a") as f:
            f.write(f"\n# Added by Bountiful's build.py: find the bountiful command\n{PATH_LINE}\n")
        print(f"    added to {_short(rc)}. Open a new terminal to use it.")
    else:
        print(f"    left {_short(rc)} alone. Add the line yourself whenever you like.")


def _short(path: Path) -> str:
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def agent_ids() -> list[str]:
    try:
        return sorted(json.loads(AGENTS_REGISTRY.read_text()).get("agents", {}))
    except (OSError, ValueError, AttributeError):
        return []


def main() -> None:
    print("Bountiful — setup")
    disable_push()
    create_venv()

    link_command()
    offer_path()

    build_infra(sys.argv[1:])

    print("\nSetup complete.")
    ids = agent_ids()
    if ids:
        print("\nStart an agent:")
        for agent_id in ids:
            print(f"    bountiful {agent_id}")
    else:
        print("\nCreate your first agent:\n\n    bountiful new")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Any running step has already said how to resume.
        sys.exit(130)
