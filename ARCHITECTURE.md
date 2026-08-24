# Architecture

build-a-bot is a template for creating local Basic Bot agents. It is not
a Python package; it contains no importable code. It is a directory of
configuration files and shim scripts that assemble an agent from two pip
dependencies: basic-bot (the engine) and basic-ui (the chat interface).

## Design Principles

**The directory is the agent.** An agent's identity, personality, and
tools all live in its repository directory. Clone the template, name
the directory, build and run the agent.

**The database is the agent's memory.** The SQLite file at
`~/.{id}/{id}.db` holds every conversation, summary, and vector
embedding the agent has ever produced. Back it up.

**dashboard.json is the source of truth.** The `id` field drives the
database filename, dot-directory path, keyring service, log prefix,
and UI title.

**Shared infrastructure, isolated data.** All agents share llama.cpp
and the embedding model at `~/.bountiful/`. Each agent's data is
isolated in its own dot-directory.

**Shim scripts stay stable.** Three of the four scripts are thin shims
that delegate to the engine or UI packages. Logic lives behind pip so
engine updates deliver new behavior without touching the agent repo.

## Files

| File | What it does |
|------|--------------|
| `dashboard.json` | Agent identity. `id` names everything; `name` is the display name. |
| `persona.md` | The agent's personality. `{{ name }}` is replaced at load time. |
| `config.json` | Agent settings. Flask port and future overrides. Missing fields use engine defaults. |
| `pyproject.toml` | Pins engine and UI versions. `packages = []` — dependencies only. |
| `build.py` | First run: names the agent, removes `.github/`, updates pyproject.toml. Every run: venv, pip install, delegates shared infrastructure to the engine (`python -m basic_bot.infra`). Idempotent. Standalone — runs before the engine exists. |
| `run.py` | Shim. Bounces into the venv, then calls `basic_ui.launch.launch(ROOT)`. |
| `add_tools.py` | Shim. Bounces into the venv, then calls `basic_bot.setup.tools.run(ROOT, args)`. Installs tool groups from extend-a-bot, including pip dependencies. `--update` refreshes code while preserving `_config.py` files. |
| `add_secrets.py` | Shim. Bounces into the venv, then calls `basic_bot.setup.secrets.run(ROOT)`. Prompts for API keys declared by the agent and its tool manifests. |
| `tools/` | Plugin tool groups. Each subdirectory is a group; `_` files are shared modules, everything else with a `TOOL` dict and `handler` is a tool. |

## Script Architecture

Three of the four scripts share the same pattern: detect whether
they're running inside the venv, bounce into it if not, then make a
single import call into the engine or UI package. The venv bounce is
stdlib-only code that never changes.

`build.py` is the exception — it runs before the venv exists. Its
pre-engine responsibilities (naming ceremony, venv creation, pip
install) must stay standalone. After pip install succeeds, it delegates
shared infrastructure setup to the engine via
`python -m basic_bot.infra`, which handles prerequisite checks,
llama.cpp compilation, and model downloads.

## Install Order

python build.py          # name, venv, pip install, infrastructure
python add_tools.py ...  # optional: install tool groups (requires venv)
python add_secrets.py    # store API keys in keyring
python run.py            # launch the agent


`build.py` must run first — everything else requires the venv it
creates.

## Naming Ceremony

On first run, `build.py` detects the sentinel `"my-agent"` in
`dashboard.json`:

1. Derives agent ID from the directory name (lowercased)
2. Derives display name (title case, hyphens/underscores to spaces)
3. Prompts for confirmation; user can override both
4. Checks for dot-directory collision (`~/.{name}/` already exists)
5. Writes `dashboard.json` (id, name) and `pyproject.toml` (name)
6. Removes `.github/` directory (upstream funding metadata)

Runs once — the sentinel check prevents re-triggering.

## How It Assembles

`run.py` calls `basic_ui.launch.launch(agent_path)`, which:

1. Loads the agent's API key from keyring into the environment
2. Reads `config.json` for agent settings (Flask port)
3. Starts llama-server for embeddings if the embedding provider is local
4. Calls `basic_ui.server.create_local_app(agent_path)`, which calls
   `basic_bot.factory.create_runtime(agent_path)`
5. Runs the Flask app
6. Tears down llama-server on exit (Ctrl+C)

The factory reads dashboard.json and persona.md, builds the SQLite
store, discovers tools, instantiates the inference provider, and returns
a `BotRuntime`. basic-ui wraps the runtime in Flask routes.

Every agent inherits the engine's three-tier memory (sliding window,
rolling summary, RAG archive), two belt tools (`search_archive`,
`recall_message`), and the inference provider abstraction. See
basic-bot's ARCHITECTURE.md for engine internals.

## Tool Groups

Each group in `tools/` carries a `tool.json` manifest declaring its
pip dependencies (installed by `add_tools.py`), keyring secrets
(prompted by `add_secrets.py`), and user config files (protected during
`--update`). Groups are self-contained — copy one to another agent and
only `_config.py` values and secrets need setting up.
