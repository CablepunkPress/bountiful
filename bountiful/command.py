"""The bountiful command: start, create, and manage agents.

USAGE below lists the commands. There is no default agent. Every
agent is started the same way, by typing its id, so starting one is
always a deliberate choice.

This is the application's policy: new agents go in the home folder by
default, an agent's data goes in the data folder inside it, and an id
starts the web page. The mechanisms it uses, creating agents, the
list of agents, and sessions, belong to basic-bot.
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
    name_from,
)

# The first word after 'bountiful' is either one of these or an
# agent's id, so no agent may be named after one of them.
COMMANDS = (
    "chat", "new", "import", "list", "forget", "models",
    "tools", "add", "remove", "keys",
    "update", "version", "help",
)

USAGE = """\
Usage:
    bountiful ID              start an agent's web page, as in 'bountiful jeden'
    bountiful chat ID         chat with an agent in the terminal
    bountiful new             name a new agent and create its folder
    bountiful import FOLDER   record an agent folder, e.g. after moving machines
    bountiful list            the agents this machine knows
    bountiful forget ID       remove an agent from the list; its folder is untouched
    bountiful models          add or remove optional chat models
    bountiful tools           the tool groups available, and which agents use each
    bountiful tools ID        an agent's tool groups, and what each still needs
    bountiful add ID GROUP    turn a tool group on for an agent
    bountiful remove ID GROUP turn it off; its settings are kept
    bountiful keys ID GROUP   store an agent's keys for a group (--delete removes them)
    bountiful update          check for a new version and install it
    bountiful version         show the installed version"""


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
    """The engine's id rules, plus this command's: no command names."""
    problem = id_problem(agent_id)
    if problem is None and agent_id in COMMANDS:
        problem = (
            f"'{agent_id}' can't be used because it's one of bountiful's "
            f"commands, so 'bountiful {agent_id}' couldn't start the agent."
        )
    return problem


def _folder(agent_id: str) -> Path:
    """The folder of the agent with this id, which must be recorded."""
    entry = registry.find(agent_id)
    if entry is None:
        _fail(
            f"No agent named '{agent_id}'. 'bountiful list' shows the agents "
            f"this machine knows; 'bountiful import FOLDER' adds one."
        )
    if not entry.present:
        _fail(
            f"{agent_id}'s folder, {_short(entry.folder)}, isn't there "
            f"anymore. If it moved, run 'bountiful import NEW_FOLDER'."
        )
    return entry.folder


# --- Commands ---

def start(agent_id: str) -> None:
    folder = _folder(agent_id)
    from basic_ui.launch import launch
    launch(folder, folder / DATA_DIR)


def chat(agent_id: str) -> None:
    folder = _folder(agent_id)
    from basic_bot.terminal import chat as terminal_chat
    terminal_chat(folder, folder / DATA_DIR)


def new() -> None:
    """Name a new agent, create its folder, and record it."""
    if not sys.stdin.isatty():
        _fail("Creating an agent asks questions, so run it in a terminal.")

    while True:
        name = input("Your agent's name: ").strip()
        agent_id = id_from(name)
        problem = _id_problem(agent_id)
        if problem is None and (taken := registry.id_taken(agent_id)):
            problem = f"Another agent already uses the id '{agent_id}', at {_short(taken)}."
        if problem is None:
            break
        print(f"  {problem}")

    # A name typed as a bare id, like "jeden", is shown as "Jeden"
    if name == agent_id:
        name = name_from(agent_id)

    folder = Path.home() / agent_id
    print(f"  id: {agent_id}")
    if not _ask(f"Create it at {_short(folder)}?", True):
        answer = input(
            f"Which folder should {name}'s folder go in? (such as ~/myAgents) "
        ).strip()
        if not answer:
            sys.exit("Nothing created.")
        folder = Path(answer).expanduser().resolve() / agent_id
        if not _ask(f"Create it at {_short(folder)}?", True):
            sys.exit("Nothing created.")
        # The user named this folder, so creating it is what they asked for
        folder.parent.mkdir(parents=True, exist_ok=True)

    try:
        folder = create_agent(folder, agent_id, name)
        registry.record(folder)
    except (AgentError, registry.RegistryError) as e:
        _fail(str(e))

    print(f"\nCreated {name} at {_short(folder)}.")
    print(f"Edit {_short(folder / 'persona.md')} to shape who {name} is.")
    print(f"Start {name} with:  bountiful {agent_id}")


def import_(path: str) -> None:
    folder = Path(path).expanduser()
    if not (folder / "agent.json").is_file() and (Path.home() / path / "agent.json").is_file():
        folder = Path.home() / path
    folder = folder.resolve()

    agent_id = load_agent(folder)["id"]
    problem = _id_problem(agent_id)
    if problem:
        _fail(f"{problem} Change the id in {_short(folder / 'agent.json')} first.")
    entry = registry.record(folder)
    print(f"Recorded {entry.agent_id} at {_short(folder)}.")
    print(f"Start it with:  bountiful {entry.agent_id}")


def list_() -> None:
    found = registry.entries()
    if not found:
        print("No agents yet. Create one with 'bountiful new'.")
        return
    for entry in found:
        where = _short(entry.folder)
        if not entry.present:
            where += "  (missing: if it moved, import it again)"
        print(f"  {entry.agent_id:<20} {where}")


def forget(agent_id: str) -> None:
    folder = registry.forget(agent_id)
    print(f"Removed {agent_id} from the list. Its folder, {_short(folder)}, is untouched.")


def models() -> None:
    """Offer the optional chat models, through the engine."""
    from basic_bot.setup.models import main as models_main
    models_main()


def _addon(action: str, *args, **kwargs) -> None:
    """Run one of extend-a-bot's add-on actions, reporting its errors.

    Imported here rather than at the top, since keyring takes a moment
    to load and only these commands need it.
    """
    from extend_a_bot import addons
    try:
        getattr(addons, action)(*args, **kwargs)
    except addons.AddonError as e:
        _fail(str(e))


def tools(args: list[str]) -> None:
    """The tool groups available, or one agent's."""
    if not args:
        present = [(e.agent_id, e.folder) for e in registry.entries() if e.present]
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
    _folder(agent_id)  # the agent must be recorded and present
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
            print("\nAgents:")
            list_()
            return

        command, rest = args[0], args[1:]
        if command == "chat":
            chat(_one(rest, "bountiful chat ID"))
        elif command == "new":
            new()
        elif command == "import":
            import_(_one(rest, "bountiful import FOLDER"))
        elif command == "list":
            list_()
        elif command == "forget":
            forget(_one(rest, "bountiful forget ID"))
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
        elif command == "version":
            version()
        elif rest:
            sys.exit(
                f"'{command}' isn't a command, and an agent's id takes "
                f"nothing after it.\n\n{USAGE}"
            )
        else:
            start(command)
    except (AgentError, registry.RegistryError) as e:
        _fail(str(e))
    except KeyboardInterrupt:
        print()
        sys.exit(130)
