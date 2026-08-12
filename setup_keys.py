"""Store this agent's API keys in the OS keyring.

Prompts for each key the agent needs, shows which are already set,
skips blanks. Run after build.py, re-run any time to add or rotate
keys. Keys never touch disk — they live in the OS-native encrypted
keyring (KWallet, GNOME Keyring, or macOS Keychain).

Tool groups that need their own secrets (see tools/README.md) use
their own keyring service names — add their entries to KEYS below.
"""

import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


# Re-exec inside the venv — keyring is installed there, not in system Python.
if sys.prefix == sys.base_prefix:
    interpreter = _venv_python()
    if not interpreter.exists():
        sys.exit("No .venv found — run 'python build.py' first.")
    os.execv(str(interpreter), [str(interpreter), *sys.argv])

# --- From here on we're inside the venv ---

import keyring
import keyring.errors

AGENT_ID = json.loads((ROOT / "dashboard.json").read_text())["id"]

# (keyring_service, key_name, human_label)
# The agent's own keys use AGENT_ID as the service. Tool-group keys
# use the group's own service name so the group is portable.
KEYS = [
    (AGENT_ID, "anthropic_api_key", "Anthropic API key"),
]


def main() -> None:
    print(f"{AGENT_ID} — API key setup\n")

    try:
        keyring.get_password(AGENT_ID, "probe")
    except keyring.errors.KeyringError as e:
        sys.exit(
            f"Could not access your system keyring: {e}\n"
            "Make sure KWallet, GNOME Keyring, or Keychain is available."
        )

    for service, key_name, label in KEYS:
        existing = keyring.get_password(service, key_name)
        status = "set" if existing else "not set"
        print(f"  {label} [{status}]")

        if existing:
            replace = input("    Replace? [y/N] ").strip().lower()
            if replace != "y":
                continue

        value = getpass.getpass(f"    {label} (hidden, Enter to skip): ").strip()
        if not value:
            print("    skipped")
            continue

        keyring.set_password(service, key_name, value)
        if keyring.get_password(service, key_name) != value:
            sys.exit("    stored but could not be read back — keyring problem")
        print("    stored")

    print("\nDone. Start the agent with:\n\n    python run.py\n")


if __name__ == "__main__":
    main()
