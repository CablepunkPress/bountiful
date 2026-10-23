"""Install Bountiful on this machine.

Installing Bountiful installs the bountiful command, the way installing
the Google Cloud SDK installs gcloud. The build asks one question
first, then does everything else on its own, so a long download can
run while no one is watching. When it says "Setup complete",
everything is ready:

    the virtual environment, with Bountiful's packages
    llama.cpp, built for this machine, in ~/.bountiful
    the AI models every agent needs, in ~/.bountiful
    the bountiful command, in ~/.local/bin and on the PATH

Optional chat models are never part of the build. They come later
with 'bountiful models', or not at all.

The question is asked once, and the answer is recorded, so re-running
after an interruption goes straight back to work and picks up where
it left off. Re-running after a system Python upgrade rebuilds the
environment for the new interpreter. No agent's files are ever touched.

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
# records the user's answer to the install question, and whether the
# build added the PATH line; agents.json is the engine's list of agents.
BOUNTIFUL_HOME = Path.home() / ".bountiful"
INSTALL_RECORD = BOUNTIFUL_HOME / "install.json"
AGENTS_REGISTRY = BOUNTIFUL_HOME / "agents.json"
MODELS_DIR = BOUNTIFUL_HOME / "models"

# The line added to a shell's startup file. It puts ~/.local/bin at the
# end of the PATH, so it never takes precedence over a command the
# user or the system already has.
PATH_LINE = 'export PATH="$PATH:$HOME/.local/bin"'
# fish's own way to say the same. --path changes PATH directly rather
# than fish_user_paths, which fish puts at the front; that change isn't
# saved on its own, so the line belongs in config.fish.
FISH_LINE = "fish_add_path --append --path $HOME/.local/bin"

# What the essential models come to across the profiles, for the
# opening statement. The build can't read the profiles yet, and on
# Linux the profile isn't known until llama.cpp is built, so this is a
# range; the exact sizes are shown before anything large downloads.
# Keep it in step with the profiles: about 31.6 GB on vulkan_12gb and
# 40.2 GB on metal_32gb (October 2026).
MODELS_SIZE = "about 30 to 40 GB"

# Set while the engine's build runs, which explains an interruption itself
_in_engine = False


def fail(message: str) -> None:
    sys.exit(f"\nERROR: {message}")


def short(path: Path) -> str:
    """A path with the home folder shown as ~."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def ask(question: str) -> bool:
    """A yes-or-no question that defaults to yes."""
    try:
        answer = input(f"{question} [Y/n] ").strip().lower()
    except EOFError:
        return False
    return answer in ("", "y", "yes")


def read_record() -> dict:
    try:
        record = json.loads(INSTALL_RECORD.read_text())
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def write_record(record: dict) -> None:
    BOUNTIFUL_HOME.mkdir(parents=True, exist_ok=True)
    INSTALL_RECORD.write_text(json.dumps(record, indent=2) + "\n")


# ---------------------------------------------------------------------------
# The shell
# ---------------------------------------------------------------------------

def shell_setup() -> tuple[Path, str] | None:
    """The user's shell startup file and the PATH line for it.

    $SHELL names the login shell, the one a new terminal window opens,
    even if this build was started from another. None for a shell
    Bountiful doesn't know.
    """
    shell = Path(os.environ.get("SHELL", "")).name
    home = Path.home()
    if shell == "zsh":
        return home / ".zshrc", PATH_LINE
    if shell == "bash":
        # On a Mac, Terminal opens login shells, which read .bash_profile
        name = ".bash_profile" if sys.platform == "darwin" else ".bashrc"
        return home / name, PATH_LINE
    if shell == "fish":
        return home / ".config" / "fish" / "config.fish", FISH_LINE
    return None


def on_path(folder: Path) -> bool:
    """True if this terminal's PATH already includes folder."""
    return any(
        Path(p).expanduser().resolve() == folder.resolve()
        for p in os.environ.get("PATH", "").split(os.pathsep) if p
    )


def in_startup_file(setup: tuple[Path, str] | None) -> bool:
    """True if the startup file already has the PATH line, so a new
    terminal window will find the command even if this one can't."""
    if setup is None:
        return False
    rc, line = setup
    try:
        return line in rc.read_text()
    except OSError:
        return False


# ---------------------------------------------------------------------------
# The question
# ---------------------------------------------------------------------------

def statement(setup: tuple[Path, str] | None) -> str:
    """What installing does, said before asking."""
    bin_dir = short(USER_BIN)
    if on_path(USER_BIN) or in_startup_file(setup):
        command = f"Installing Bountiful puts the bountiful command in {bin_dir}."
    elif setup is not None:
        command = (
            f"Installing Bountiful puts the bountiful command in {bin_dir}\n"
            f"and adds {bin_dir} to your PATH in {short(setup[0])}."
        )
    else:
        command = (
            f"Installing Bountiful puts the bountiful command in {bin_dir}.\n"
            f"Your shell isn't one Bountiful knows, so at the end it shows\n"
            f"the line that lets your terminal find the command."
        )

    if any(MODELS_DIR.glob("*.gguf")):
        models = (
            "It also checks the AI models in ~/.bountiful and downloads any\n"
            "that are missing or out of date."
        )
    else:
        models = (
            f"It also downloads 3 AI models into ~/.bountiful, {MODELS_SIZE}\n"
            "depending on your machine. Their exact sizes are shown before\n"
            "the download begins.\n"
            "\n"
            "On a slow connection this can take hours. If it's interrupted,\n"
            "run python3 build.py again and it picks up where it stopped."
        )
    return f"{command}\n{models}"


def agree(record: dict, setup: tuple[Path, str] | None) -> bool:
    """Ask, once, whether to install. False if the answer is no.

    The answer is recorded, so a re-run goes straight back to work.
    With no one at the keyboard, as when an app or a script runs the
    build, it installs without asking but leaves the shell's startup
    file alone, since that's the one thing outside Bountiful's own
    folders, and nothing is recorded.
    """
    if record.get("installed"):
        return True

    print()
    print(statement(setup))
    print()

    if not sys.stdin.isatty():
        print(
            "No one is at the keyboard, so Bountiful installs without asking\n"
            "and leaves your shell's startup file alone."
        )
        return True

    if not ask("Install Bountiful?"):
        return False
    record["installed"] = True
    write_record(record)
    return True


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


def create_venv() -> None:
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
        print(f"    created a virtual environment in {short(VENV)}")
    else:
        print(f"    using the virtual environment in {short(VENV)}")

    print("    installing Bountiful's packages from GitHub")
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


def build_engine() -> None:
    """llama.cpp, the hardware profile, and the models, by the engine."""
    global _in_engine
    _in_engine = True
    result = subprocess.run([str(venv_python()), "-m", "basic_bot"])
    _in_engine = False
    if result.returncode != 0:
        # basic_bot has already explained what failed and what to do.
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# The bountiful command
# ---------------------------------------------------------------------------

def link_command() -> None:
    """Link ~/.local/bin/bountiful to this clone's command.

    This is part of installing Bountiful, so it happens on every build.
    A link or file there that isn't this clone's is left alone.
    """
    if LINK.is_symlink() and LINK.resolve() == venv_command().resolve():
        print(f"    installed in {short(USER_BIN)}")
        return
    if LINK.exists() or LINK.is_symlink():
        print(
            f"    {short(LINK)} already exists and isn't this clone's command, "
            f"so it was left alone.\n"
            f"    Remove it, then build again, to use this one."
        )
        return
    USER_BIN.mkdir(parents=True, exist_ok=True)
    LINK.symlink_to(venv_command())
    print(f"    installed in {short(USER_BIN)}")
    print(f"      (to remove it: rm {short(LINK)})")


def put_on_path(record: dict, setup: tuple[Path, str] | None,
                may_edit: bool) -> str:
    """Make sure new terminals find the command.

    Returns "ready" if this terminal already finds it, "new terminal"
    if a new terminal window will, and "by hand" if the user has to add
    the line themselves. A line the build added once and the user later
    removed isn't added again.
    """
    if on_path(USER_BIN):
        return "ready"
    if in_startup_file(setup):
        return "new terminal"

    if setup is not None and may_edit and not record.get("path_added"):
        rc, line = setup
        rc.parent.mkdir(parents=True, exist_ok=True)
        with open(rc, "a") as f:
            f.write(f"\n# Added by Bountiful: find the bountiful command\n{line}\n")
        record["path_added"] = True
        write_record(record)
        print(f"    added {short(USER_BIN)} to your PATH in {short(rc)}")
        return "new terminal"

    where = f"to {short(setup[0])}" if setup else "to your shell's startup file"
    line = setup[1] if setup else PATH_LINE
    print(
        f"    {short(USER_BIN)} isn't on your PATH. To type 'bountiful' "
        f"anywhere,\n    add this line {where},\n    then open a new "
        f"terminal window:\n\n        {line}"
    )
    return "by hand"


# ---------------------------------------------------------------------------
# The end
# ---------------------------------------------------------------------------

def agent_ids() -> list[str]:
    try:
        return sorted(json.loads(AGENTS_REGISTRY.read_text()).get("agents", {}))
    except (OSError, ValueError, AttributeError):
        return []


def closing(path_state: str) -> str:
    """The last words: what to type next."""
    command = "bountiful" if path_state != "by hand" else short(LINK)
    if path_state == "new terminal":
        first = "Open a new terminal window, then"
    elif path_state == "by hand":
        first = f"Until {short(USER_BIN)} is on your PATH,"
    else:
        first = ""

    ids = agent_ids()
    if ids:
        lead = f"{first} start an agent:" if first else "Start an agent:"
        lines = [f"Setup complete. {lead}", ""]
        lines += [f"    {command} {agent_id}" for agent_id in ids]
        return "\n".join(lines)

    run = f"Setup complete. {first} run" if first else "Setup complete. Run"
    rest = f"'{command} new' to create your first agent."
    # One line if it fits, otherwise broken before the command, so the
    # command is never split
    joiner = " " if len(run) + len(rest) < 64 else "\n"
    return f"{run}{joiner}{rest}"


def main() -> None:
    if sys.argv[1:]:
        if "--models" in sys.argv[1:]:
            sys.exit("Optional models are chosen with 'bountiful models' now.")
        sys.exit("python3 build.py takes no options.")

    print("Bountiful — setup")
    record = read_record()
    setup = shell_setup()
    if not agree(record, setup):
        print("\nNothing was installed.")
        return

    print("\nPython environment")
    disable_push()
    create_venv()

    build_engine()

    print("\nThe bountiful command")
    link_command()
    path_state = put_on_path(record, setup, may_edit=bool(record.get("installed")))

    print()
    print(closing(path_state))
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if not _in_engine:
            print("\n\nStopped. Run 'python3 build.py' again to carry on.")
        sys.exit(130)
