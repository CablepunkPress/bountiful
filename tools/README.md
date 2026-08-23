# Tools

Drop tool groups here. A tool group is a directory of Python files:

    tools/
    ├── github/
    │   ├── _auth.py            ← shared code, not a tool
    │   ├── create_branch.py    ← a tool
    │   └── read_file.py        ← a tool
    └── example/
        ├── _config.py          ← shared configuration
        └── some_tool.py        ← a tool

Each tool file defines a TOOL dict (the schema) and a handler function.
Files starting with _ are shared modules — tool files in the same group
import them directly: `from _auth import auth_headers`.

Tool groups that need API keys use their own keyring service name.
Add the group's keys to add_secrets.py KEYS and re-run it.

The agent discovers everything here at startup. No registration,
no imports, no configuration — the directory is the installation.

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

```
python add_tools.py <toolgroup> --update
```

This fetches the latest from extend-a-bot while preserving your `_config.py` settings.
