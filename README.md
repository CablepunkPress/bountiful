# build-a-bot

Name and customize your own Basic Bot Engine agent.

## Installation

Name your agent what you wish. The example here is Alice.

`python add_tool.py github` is optional.

`python setup_keys.py` is currently manadatory since a full local build is not yet completed.

```bash
git clone https://github.com/CablepunkPress/build-a-bot.git alice
cd alice
# edit dashboard.json — set id to "alice"
# edit persona.md — set name to Alice and provide a personality 
python add_tool.py github
# edit tools/github/_auth.py — fill in your values
python build.py
python setup_keys.py
python run.py
```
