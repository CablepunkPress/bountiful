# Build-A-Bot

## Who This Is For

Developers who want to build AI agents that run locally on their own machine. Configure your agent via the command line, then interact with it through a web interface in your browser. You have full control over behavior, tools, and data.

## The Ecosystem

| Repo | What it is |
|------|------------|
| [basic-bot](https://github.com/CablepunkPress/basic-bot) | The engine. Chat loop, memory, tool system. |
| [basic-ui](https://github.com/CablepunkPress/basic-ui) | Reference Flask chat interface. |
| [build-a-bot](https://github.com/CablepunkPress/build-a-bot) | Template for creating your own local agent. |
| [extend-a-bot](https://github.com/CablepunkPress/extend-a-bot) | Drop-in plugin tool groups. |

## Installation

Clone this repo and run:

```bash
python build.py
```

This scaffolds your agent, installs dependencies, and sets up the local inference pipeline.

## Adding Tools

Tools come from the [extend-a-bot](https://github.com/CablepunkPress/extend-a-bot) repository. To add a tool group to your agent:

1. Run `python add_tools.py <toolgroup>` from the project root
   - Example: `python add_tools.py github`
   - This fetches tools from extend-a-bot and creates `tools/<toolgroup>/`

2. Configure credentials and settings
   - Edit `tools/<toolgroup>/_config.py` with your configuration
   - Use `python add_secrets.py` to store sensitive credentials in your keyring

3. Restart the agent
   - Tools are auto-discovered at startup
   - Run `python run.py` to start the agent with new tools loaded

## Updating Tools

To pull the latest versions of tools you've already installed:

```bash
python add_tools.py <toolgroup> --update
```

This fetches the latest from extend-a-bot while preserving your `_config.py` settings.

## How It Works

Tools live in subdirectories under `tools/`. Each subdirectory (e.g., `tools/github/`) contains:

- Individual tool files (one per tool)
- `_auth.py` — authentication and API logic
- `_config.py` — user configuration
- `tool.json` — tool manifest

The agent auto-discovers all tools at startup and makes them available in the chat.
