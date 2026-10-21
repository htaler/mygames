"""Epic via legendary (https://github.com/derrod/legendary), which owns the OAuth and catalog lookups.

Uses an installed `legendary` if present, otherwise runs it through `uvx` with no global install.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from ..matching import Ownership


def _legendary() -> list[str]:
    if shutil.which("legendary"):
        return ["legendary"]
    if shutil.which("uvx"):
        return ["uvx", "--from", "legendary-gl", "legendary"]
    raise SystemExit("Need `legendary` or `uvx` on PATH for Epic support.")


def is_configured() -> bool:
    home = Path(os.environ.get("LEGENDARY_CONFIG_PATH", Path.home() / ".config" / "legendary"))
    return (home / "user.json").exists()


def login() -> None:
    cmd = _legendary() + ["auth"]
    os.execvp(cmd[0], cmd)


def _list(platform: str) -> list[dict]:
    cmd = _legendary() + ["list", "--json", "--include-non-installable", "--platform", platform]
    # legendary logs to stderr; only stdout is the JSON payload.
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"legendary failed (logged in? run: mygames login epic)\n{proc.stderr.strip()}")
    return json.loads(proc.stdout)


def fetch() -> list[Ownership]:
    # legendary lists only Mac builds by default on macOS; ownership is mostly Windows builds.
    games = {}
    for platform in ("Windows", "Mac"):
        for g in _list(platform):
            games.setdefault(g["app_name"], Ownership("epic", g["app_name"], g.get("app_title") or g["app_name"]))
    return list(games.values())
