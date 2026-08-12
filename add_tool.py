"""Install a tool group from the extend-a-bot repository.

Downloads the tool group from CablepunkPress/extend-a-bot on GitHub
and copies it into this agent's tools/ directory. After installation,
edit the configuration values and run setup_keys.py for any new secrets.

Usage:
    python add_tool.py github
    python add_tool.py github --force    (overwrite existing)
    python add_tool.py --list            (show available groups)

Runs with system Python — no venv needed.
"""

import io
import json
import os
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS_DIR = ROOT / "tools"

REPO_OWNER = "CablepunkPress"
REPO_NAME = "extend-a-bot"
REPO_BRANCH = "main"
TARBALL_URL = (
    f"https://github.com/{REPO_OWNER}/{REPO_NAME}"
    f"/archive/refs/heads/{REPO_BRANCH}.tar.gz"
)


def fail(message: str) -> None:
    sys.exit(f"\nERROR: {message}")


def fetch_tarball() -> tarfile.TarFile:
    """Download the extend-a-bot repo as a tarball."""
    print(f"Fetching {REPO_OWNER}/{REPO_NAME}...")
    try:
        with urllib.request.urlopen(TARBALL_URL) as response:
            data = response.read()
    except urllib.error.URLError as e:
        fail(f"Could not download extend-a-bot: {e}")

    return tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")


def list_groups(tar: tarfile.TarFile) -> list[str]:
    """Find all tool groups in the tarball (directories with tool.json)."""
    # GitHub tarballs have a top-level directory: extend-a-bot-main/
    prefix = f"{REPO_NAME}-{REPO_BRANCH}/"
    groups = set()

    for member in tar.getmembers():
        if not member.name.startswith(prefix):
            continue
        relative = member.name[len(prefix):]
        parts = relative.split("/")
        if len(parts) == 2 and parts[1] == "tool.json":
            groups.add(parts[0])

    return sorted(groups)


def extract_group(tar: tarfile.TarFile, group_name: str) -> None:
    """Extract one tool group into tools/."""
    prefix = f"{REPO_NAME}-{REPO_BRANCH}/{group_name}/"
    dest = TOOLS_DIR / group_name

    members = [
        m for m in tar.getmembers()
        if m.name.startswith(prefix) and m.name != prefix
    ]

    if not members:
        fail(f"Tool group '{group_name}' not found in extend-a-bot")

    dest.mkdir(parents=True, exist_ok=True)

    for member in members:
        relative = member.name[len(prefix):]
        target = dest / relative

        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        elif member.isfile():
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src:
                if src is None:
                    continue
                target.write_bytes(src.read())

    print(f"Installed tools/{group_name}/")


def print_next_steps(group_dir: Path) -> None:
    """Read tool.json and print what the user does next."""
    manifest_path = group_dir / "tool.json"
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())

    print(f"\n--- {manifest.get('name', group_dir.name)} ---")
    print(f"{manifest.get('description', '')}")

    config_items = manifest.get("config", [])
    secrets = manifest.get("secrets", [])
    deps = manifest.get("dependencies", [])

    steps = []

    if config_items:
        files = sorted(set(c["file"] for c in config_items))
        lines = []
        for c in config_items:
            lines.append(f"     {c['name']} — {c['label']}")
        steps.append(
            f"Edit tools/{group_dir.name}/{files[0]}:\n" + "\n".join(lines)
        )

    if secrets:
        steps.append(
            f"Run: python setup_keys.py   ({len(secrets)} key(s) needed)"
        )

    if deps:
        steps.append(
            f"Run: python build.py        (installs: {', '.join(deps)})"
        )

    if steps:
        print("\nNext steps:")
        for i, s in enumerate(steps, 1):
            print(f"  {i}. {s}")
    print()


def cmd_list() -> None:
    """List available tool groups."""
    tar = fetch_tarball()
    groups = list_groups(tar)

    if not groups:
        print("No tool groups found in extend-a-bot.")
        return

    print(f"\nAvailable tool groups ({len(groups)}):\n")
    for name in groups:
        prefix = f"{REPO_NAME}-{REPO_BRANCH}/{name}/tool.json"
        member = None
        try:
            member = tar.getmember(prefix)
        except KeyError:
            pass

        description = ""
        if member:
            with tar.extractfile(member) as f:
                if f:
                    manifest = json.loads(f.read())
                    description = manifest.get("description", "")

        installed = (TOOLS_DIR / name).exists()
        status = " (installed)" if installed else ""
        print(f"  {name}{status}")
        if description:
            print(f"    {description}")
    print(f"\nInstall with: python add_tool.py <name>")


def cmd_install(group_name: str, force: bool = False) -> None:
    """Install a tool group."""
    dest = TOOLS_DIR / group_name

    if dest.exists() and not force:
        fail(
            f"tools/{group_name}/ already exists. Your edits would be lost.\n"
            f"To overwrite: python add_tool.py {group_name} --force"
        )

    tar = fetch_tarball()
    groups = list_groups(tar)

    if group_name not in groups:
        fail(
            f"Tool group '{group_name}' not found.\n"
            f"Available: {', '.join(groups) or 'none'}\n"
            f"Run: python add_tool.py --list"
        )

    extract_group(tar, group_name)
    print_next_steps(dest)


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "Usage:\n"
            "  python add_tool.py <group>         Install a tool group\n"
            "  python add_tool.py <group> --force  Overwrite existing\n"
            "  python add_tool.py --list           Show available groups"
        )
        return

    if args[0] == "--list":
        cmd_list()
        return

    group_name = args[0]
    force = "--force" in args
    cmd_install(group_name, force)


if __name__ == "__main__":
    main()
