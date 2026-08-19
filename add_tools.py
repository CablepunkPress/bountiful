"""Install a tool group from the extend-a-bot repository.

    python add_tools.py --list
    python add_tools.py github
    python add_tools.py github --update
    python add_tools.py github --force
    
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def _venv_python():
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


if sys.prefix == sys.base_prefix:
    interpreter = _venv_python()
    if not interpreter.exists():
        sys.exit("No .venv found — run 'python build.py' first.")
    os.execv(str(interpreter), [str(interpreter), *sys.argv])

# --- Inside venv ---
from basic_bot.setup.tools import run

run(ROOT, sys.argv[1:])
