# build-a-bot

Name and customize your own Basic Bot Engine agent.

## Installation

Name your agent what you wish. The example here is Alice.

`python add_tool.py github` is optional.

```bash
git clone https://github.com/CablepunkPress/build-a-bot.git alice
cd alice
```

Edit three files to name your agent:

- `dashboard.json` — set `id` to `"alice"`
- `pyproject.toml` — set `name` to `"alice"`
- `persona.md` — give your agent a personality

Then build and run:

```bash
python build.py
python setup_keys.py
python run.py
```

## Adding tools (optional)

```bash
python add_tool.py --list
python add_tool.py github
# edit tools/github/_auth.py — fill in your values
python build.py
python setup_keys.py
python run.py
```
