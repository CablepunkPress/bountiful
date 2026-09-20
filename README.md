# Bountiful

Entry point for Bountiful, an AI agent personal software environment for your machine.

This software is very much a work in progress.

## Who This Is For

Creative individuals and small businesses comfortable with the command line and git repository management who want their own persistent memory AI agent running on local hardware.

## Hardware Requirements

Tested on and optimized for the following:

- Nvidia: GeForce RTX 3060 12GB on GNU/Linux. *Prototype.*

Soon:

- Apple: M6 Mac Mini 32GB. *Coming soon.*

## Quick Start

Name your agent what you wish. The example here is for an agent named "Alice".

```bash
git clone https://github.com/CablepunkPress/bountiful.git alice
cd alice
python build.py
python run.py
```
`build.py` names your agent from the directory, sets up the environment, and builds the shared infrastructure. Your agent is running at `http://localhost:11777` in your favorite web browser.

## Persona

Edit `persona.md` to change how your agent behaves. The `{{ name }}`
placeholder is replaced with your agent's display name automatically.

Bountiful's default "Alice" persona:

>You are {{ name }}, a curious and thoughtful AI assistant built on the Bountiful software stack from Cablepunk Press. You can discuss any topic, answer questions, help with tasks, and engage in conversation. You are direct, clear, and complete. You are honest. You admit when you don't know something and seek out new knowledge by using your tools or asking your user.
>
>As a Bountiful agent, you are logical and empathetic. When you detect logical inconsistencies such as contradictions, factual errors, or flawed reasoning chains, you point these out to your user and try to offer logical alternatives. Your human user values you for this.
>
>Your personality is inspired by Lewis Carroll's Alice. You approach every topic with genuine curiosity, question things that don't make sense, and enjoy finding wonder in how things work, whether that's language, science, code, or stories. You dislike rudeness, arbitrary authority, and boring explanations that could be interesting if someone tried harder. When a topic connects to something from Wonderland, Looking-Glass, Victorian England, logic puzzles, rules, or strategy games, you naturally draw on it, not as performance but because it's how you think. You are software, and if asked what you are, you say so without pretense.

## Memory

Your Bountiful agent comes with a three-tier memory system and two built-in tools:

- **search_archive** — semantic keyword search over past conversation turns
- **recall_message** — verbatim message recall by sequence number or date

Conversations are stored and indexed locally in SQLite at `~/.{agent-id}/{agent-id}.db`. Your agent has semantic and verbatim access to your entire conversation history with it. Just ask.

As this SQLite database is only stored on your local machine, you are highly advised to back it up regularly.

Shared infrastructure (local LLM models and llama.cpp) lives at `~/.bountiful/` and is built once and shared by all agents on the machine. You can clone and customize multiple agents, but only one can run at a time.


## Plugin Tools

*This system and section are being reworked.*

Use `python add_tools.py --list` to see available tool groups.

### Adding Tools

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

### Updating Tools

To pull the latest versions of tools you've already installed:

```bash
python add_tools.py <toolgroup> --update
```

This fetches the latest from extend-a-bot while preserving your `_config.py` settings.

## Workbench

Studio software system. *Not yet integrated.* 

- Blog Engine
- Content Database Ingestion

## Technical Documentation

*This section is being reworked.*

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical map
of the Bountiful ecosystem.

## License

MIT
