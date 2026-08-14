"""Store this agent's API keys in the OS keyring.

Scans tools/*/tool.json for secret declarations and merges them
with the agent's own keys. Shows what's set, prompts for what's
missing. Run any time to add or rotate keys.

    python add_secrets.py
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


# Re-exec inside the venv — keyring is installed there.
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
KEYS: list[tuple[str, str, str]] = [
    (AGENT_ID, "anthropic_api_key", "Anthropic API key"),
]


def _discover_tool_secrets() -> list[tuple[str, str, str]]:
    """Scan tools/*/tool.json for secret declarations."""
    tools_dir = ROOT / "tools"
    if not tools_dir.is_dir():
        return []

    secrets = []
    for manifest_path in sorted(tools_dir.glob("*/tool.json")):
        manifest = json.loads(manifest_path.read_text())
        group_name = manifest_path.parent.name
        for s in manifest.get("secrets", []):
            secrets.append((
                s["service"],
                s["key"],
                f"{s['label']} ({group_name})",
            ))
    return secrets


def main() -> None:
    print(f"{AGENT_ID} — API key setup\n")

    try:
        keyring.get_password(AGENT_ID, "probe")
    except keyring.errors.KeyringError as e:
        sys.exit(
            f"Could not access your system keyring: {e}\n"
            "Make sure KWallet, GNOME Keyring, or Keychain is available."
        )

    all_keys = KEYS + _discover_tool_secrets()

    for service, key_name, label in all_keys:
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
