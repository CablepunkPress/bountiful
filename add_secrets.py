"""Store this agent's API keys in the OS keyring.

    python add_secrets.py
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


def _venv_version():
    """The major.minor Python version recorded in the venv, or None."""
    cfg = VENV / "pyvenv.cfg"
    if not cfg.exists():
        return None
    for line in cfg.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() in ("version", "version_info"):
            try:
                major, minor = value.strip().split(".")[:2]
                return int(major), int(minor)
            except ValueError:
                return None
    return None


if Path(sys.prefix).resolve() != VENV.resolve():
    if not VENV.exists():
        sys.exit("No .venv found — run 'python build.py' first.")
    built = _venv_version()
    running = sys.version_info[:2]
    if built != running or not _venv_python().exists():
        was = f"{built[0]}.{built[1]}" if built else "an unknown version"
        sys.exit(
            f"This agent's environment was built with Python {was}, "
            f"but your system now runs Python {running[0]}.{running[1]}.\n"
            "Run 'python build.py' to rebuild it, then try again. "
            "Your agent's memory and settings are not affected."
        )
    os.execv(str(_venv_python()), [str(_venv_python()), *sys.argv])

# --- Inside venv ---
from basic_bot.setup.secrets import run

run(ROOT)
