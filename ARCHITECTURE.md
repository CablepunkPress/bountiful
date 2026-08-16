# Architecture

build-a-bot is a template for creating local Basic Bot agents. It is not
a Python package; it contains no importable code. It is a directory of
configuration files and scripts that assemble an agent from two pip
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

## Files

| File | What it does |
|------|--------------|
| `dashboard.json` | Agent identity. `id` names everything; `name` is the display name. |
| `persona.md` | The agent's personality. `{{ name }}` is replaced at load time. |
| `config.py` | Runtime settings. Just the Flask port. |
| `pyproject.toml` | Pins engine and UI versions. `packages = []` — dependencies only. |
| `build.py` | First run: names the agent from the directory. Every run: venv, pip install, tool dependencies, shared infrastructure at `~/.bountiful/`. Idempotent. |
| `run.py` | Bootstraps into the venv, reads the API key from keyring, ensures llama-server is up, launches the Flask UI. |
| `add_tools.py` | Installs tool groups from extend-a-bot. `--update` refreshes code while preserving `_config.py` files. |
| `add_secrets.py` | Prompts for API keys declared by the agent and its tool manifests. Stores in the OS keyring. |
| `tools/` | Plugin tool groups. Each subdirectory is a group; `_` files are shared modules, everything else with a `TOOL` dict and `handler` is a tool. |

## How It Assembles

`run.py` calls `basic_ui.server.create_local_app(agent_path)`, which
calls `basic_bot.factory.create_runtime(agent_path)`. The factory reads
dashboard.json and persona.md, builds the SQLite store, and discovers
tools. basic-ui wraps the resulting runtime in Flask routes.

Every agent inherits the engine's three-tier memory (sliding window,
rolling summary, RAG archive) and two belt tools (`search_archive`,
`recall_message`). See basic-bot's ARCHITECTURE.md for engine internals.

## Tool Groups

Each group in `tools/` carries a `tool.json` manifest declaring its
pip dependencies (installed by `build.py`), keyring secrets (prompted
by `add_secrets.py`), and user config files (protected during
`--update`). Groups are self-contained — copy one to another agent and
only `_config.py` values and secrets need setting up.
