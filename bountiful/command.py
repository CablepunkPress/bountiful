"""The bountiful command: start, create, and manage agents.

USAGE below lists the subcommands. The first word after 'bountiful'
is one slot, filled by two lists: SUBCOMMANDS, the same on every
machine, and the registered agents' ids, different on every machine.
A registered id starts that agent, so there is no default agent, and
starting one is always a deliberate choice.

Every agent lives in the home folder, at ~/ID, and its data in the
data folder inside it. The mechanisms this uses, creating an agent,
the registry, and sessions, belong to basic-bot.
"""

import os
import sys
from pathlib import Path
from typing import NoReturn

import bountiful
from basic_bot import registry
from basic_bot.agent import (
    DATA_DIR,
    AgentError,
    create_agent,
    id_from,
    id_problem,
    load_agent,
)

# Every subcommand. The first word after 'bountiful' is either one of
# these or a registered id, and these are checked first, so no agent's
# id may be one of them. A word likely to become a subcommand can be
# added here ahead of time, with a note saying so.
SUBCOMMANDS = (
    "create", "agents", "register", "forget", "chat", "models",
    "tools", "add", "remove", "keys",
    "update", "version", "help",
)

USAGE = """\
Usage:
    bountiful create NAME     create a new agent, as in 'bountiful create Alice'
    bountiful ID              start an agent, as in 'bountiful alice'
    bountiful agents          the agents this machine knows
    bountiful models          add or remove optional chat models
    bountiful tools           the tool groups available, and which agents use each
    bountiful tools ID        an agent's tool groups, and what each still needs
    bountiful add ID GROUP    turn a tool group on for an agent
    bountiful remove ID GROUP turn it off; its settings are kept
    bountiful keys ID GROUP   store an agent's keys for a group (--delete removes them)
    bountiful register ID     register an agent's folder in home
    bountiful forget ID       unregister an agent; its folder is untouched
    bountiful version         show the installed version
    bountiful update          check for a new version and install it"""


def _fail(message: str) -> NoReturn:
    sys.exit(f"ERROR: {message}")


def _ask(question: str, default: bool) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{question} {hint} ").strip().lower()
    except EOFError:
        return default
    return default if not answer else answer in ("y", "yes")


def _short(path: Path) -> str:
    """A path with the home folder shown as ~."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def _id_problem(agent_id: str) -> str | None:
    """The engine's id rules, plus this command's: no subcommands."""
    problem = id_problem(agent_id)
    if problem is None and agent_id in SUBCOMMANDS:
        problem = f"'{agent_id}' is a subcommand."
    return problem


def _folder(agent_id: str) -> Path:
    """The folder of a registered agent, which must still be there."""
    if not registry.registered(agent_id):
        _fail(f"'{agent_id}' does not exist.")
    folder = registry.folder(agent_id)
    if not (folder / "agent.json").is_file():
        _fail(f"{_short(folder)} is missing.")
    return folder


# --- Subcommands ---

def start(agent_id: str) -> None:
    folder = _folder(agent_id)
    from basic_ui.launch import launch
    launch(folder, folder / DATA_DIR)


def chat(agent_id: str) -> None:
    folder = _folder(agent_id)
    from basic_bot.terminal import chat as terminal_chat
    terminal_chat(folder, folder / DATA_DIR)


def _in_home(agent_id: str) -> bool:
    """Whether home already holds something by this name, in any case.

    A Mac's disk ignores case and Linux's doesn't, so ~/Music blocks
    music on both.
    """
    return any(entry.name.lower() == agent_id for entry in Path.home().iterdir())


def _free_id(base: str) -> str:
    """The first usable id from base: base, then base-1, base-2, and so on.

    An id is usable if it isn't a subcommand or reserved, isn't
    registered, and nothing in home has its name.
    """
    n = 0
    while True:
        agent_id = f"{base}-{n}" if n else base
        if not (
            _id_problem(agent_id)
            or registry.registered(agent_id)
            or _in_home(agent_id)
        ):
            return agent_id
        n += 1


def create(words: list[str]) -> None:
    """Create a new agent from its name, in ~/ID, and register it."""
    name = " ".join(words).strip()
    if not name:
        sys.exit("Usage: bountiful create NAME, as in 'bountiful create Alice'")
    if not sys.stdin.isatty():
        _fail("Creating an agent asks before it creates, so run it in a terminal.")

    base = id_from(name)
    if not base:
        _fail(
            f"Couldn't make an id from '{name}'. "
            f"Use a name with Latin letters or numbers."
        )

    agent_id = _free_id(base)
    folder = registry.folder(agent_id)
    try:
        agreed = _ask(f"Create {name} with ID={agent_id} at {_short(folder)}?", True)
    except KeyboardInterrupt:
        print()
        agreed = False
    if not agreed:
        print("No new agent was created.")
        return

    create_agent(folder, agent_id, name)
    registry.register(agent_id)
    print(f"\nCreated {name} at {_short(folder)}.")
    print(f"Start {name} with 'bountiful {agent_id}'.")


def register(agent_id: str) -> None:
    problem = _id_problem(agent_id)
    if problem:
        _fail(problem)
    registry.register(agent_id)
    print(f"Registered {agent_id}.")


def forget(agent_id: str) -> None:
    registry.forget(agent_id)
    print(f"Forgot {agent_id}. Its folder is untouched.")


def agents() -> None:
    """The registered agents, with each one's name and folder."""
    rows = [("ID", "NAME", "FOLDER")]
    for agent_id in registry.ids():
        folder = registry.folder(agent_id)
        try:
            name = load_agent(folder)["name"]
            where = _short(folder)
        except AgentError:
            name, where = "", "Missing"
        rows.append((agent_id, name, where))

    if len(rows) == 1:
        print("No agents yet.")
        return
    id_width = max(len(r[0]) for r in rows) + 4
    name_width = max(len(r[1]) for r in rows) + 4
    for agent_id, name, where in rows:
        print(f"{agent_id:<{id_width}}{name:<{name_width}}{where}")


def models() -> None:
    """Offer the optional chat models, through the engine."""
    from basic_bot.setup.models import main as models_main
    models_main()


def _addon(action: str, *args, **kwargs) -> None:
    """Run one of extend-a-bot's add-on actions, reporting its errors.

    Imported here rather than at the top, since keyring takes a moment
    to load and only these subcommands need it.
    """
    from extend_a_bot import addons
    try:
        getattr(addons, action)(*args, **kwargs)
    except addons.AddonError as e:
        _fail(str(e))


def tools(args: list[str]) -> None:
    """The tool groups available, or one agent's."""
    if not args:
        present = [
            (agent_id, registry.folder(agent_id))
            for agent_id in registry.ids()
            if (registry.folder(agent_id) / "agent.json").is_file()
        ]
        _addon("show_available", present)
    elif len(args) == 1:
        _addon("show_agent", args[0], _folder(args[0]))
    else:
        sys.exit("Usage: bountiful tools [ID]")


def add(agent_id: str, group: str) -> None:
    _addon("add", agent_id, _folder(agent_id), group)


def remove(agent_id: str, group: str) -> None:
    _addon("remove", agent_id, _folder(agent_id), group)


def keys(args: list[str]) -> None:
    delete = "--delete" in args
    rest = [a for a in args if a != "--delete"]
    if len(rest) != 2:
        sys.exit("Usage: bountiful keys ID GROUP [--delete]")
    agent_id, group = rest
    _folder(agent_id)  # the agent must be registered and present
    _addon("keys", agent_id, group, delete=delete)


def version() -> None:
    print(f"bountiful {bountiful.__version__}")


def update() -> None:
    """Install the newest release, if there is one.

    Releases are tags, and the stable branch only ever moves to the
    newest one, so updating means following stable. A clone on any
    other branch, such as main for development, is left to git pull
    and python3 build.py.
    """
    clone = Path(sys.prefix).parent

    if not (clone / ".git").is_dir():
        _fail(
            "This isn't a git clone, so it can't update itself.\n"
            "Download a fresh copy from the README instead."
        )

    import shutil
    import subprocess

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(clone), *args], capture_output=True, text=True,
        )

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != "stable":
        print(
            f"This clone is on '{branch}', not stable, so 'bountiful update' "
            f"leaves it alone.\nIt follows releases only. To get the newest "
            f"code, run 'git pull', then 'python3 build.py'."
        )
        return

    if git("status", "--porcelain").stdout.strip():
        _fail(
            "This clone has local changes. Discard them first,\n"
            "then run 'bountiful update' again."
        )

    if git("fetch", "--tags", "origin").returncode != 0:
        _fail(
            "Couldn't reach GitHub. Check your connection,\n"
            "then run 'bountiful update' again."
        )

    if git("rev-parse", "HEAD").stdout == git("rev-parse", "origin/stable").stdout:
        print(f"Already up to date (v{bountiful.__version__}).")
        return

    # stable only moves to release tags, so it should name one; its
    # message is the release notes
    tag = git("describe", "--exact-match", "origin/stable").stdout.strip()
    if tag:
        print(f"Bountiful {tag} is available (you have v{bountiful.__version__}).")
        notes = git("tag", "-l", "--format=%(contents)", tag).stdout.strip()
        if notes:
            print(f"\n{notes}")
    else:
        print(f"A new release is available (you have v{bountiful.__version__}).")
    print()

    if sys.stdin.isatty() and not _ask("Update?", True):
        print("Nothing changed.")
        return

    pull = git("pull", "--ff-only")
    if pull.returncode != 0:
        _fail(
            "The update couldn't be applied. The output:\n\n"
            + (pull.stderr or pull.stdout)
        )

    # Rebuild exactly as the user would: python3 build.py, with whatever
    # python3 the terminal finds. build.py runs on the system Python
    # because it may rebuild the venv, and checks the version itself.
    system_python = shutil.which("python3")
    if system_python is None:
        _fail("Updated, but python3 isn't on the PATH. Run 'python3 build.py' to finish.")

    print("\nRebuilding...\n", flush=True)
    os.execv(system_python, [system_python, str(clone / "build.py")])


# --- Dispatch ---

def _one(args: list[str], usage: str) -> str:
    if len(args) != 1:
        sys.exit(f"Usage: {usage}")
    return args[0]


def _two(args: list[str], usage: str) -> tuple[str, str]:
    if len(args) != 2:
        sys.exit(f"Usage: {usage}")
    return args[0], args[1]


def main() -> None:
    args = sys.argv[1:]

    try:
        if not args or args[0] in ("help", "-h", "--help"):
            print(USAGE)
            return

        command, rest = args[0], args[1:]
        if command == "create":
            create(rest)
        elif command == "agents":
            agents()
        elif command == "register":
            register(_one(rest, "bountiful register ID"))
        elif command == "forget":
            forget(_one(rest, "bountiful forget ID"))
        elif command == "chat":
            chat(_one(rest, "bountiful chat ID"))
        elif command == "models":
            models()
        elif command == "tools":
            tools(rest)
        elif command == "add":
            add(*_two(rest, "bountiful add ID GROUP"))
        elif command == "remove":
            remove(*_two(rest, "bountiful remove ID GROUP"))
        elif command == "keys":
            keys(rest)
        elif command == "update":
            update()
        elif command in ("version", "-v", "-V", "--version"):
            version()
        elif not registry.registered(command):
            sys.exit(f"'{command}' is not a subcommand. Run 'bountiful' for a list.")
        elif rest:
            sys.exit(f"'{command}' takes nothing after it.")
        else:
            start(command)
    except (AgentError, registry.RegistryError) as e:
        _fail(str(e))
    except KeyboardInterrupt:
        print()
        sys.exit(130)
