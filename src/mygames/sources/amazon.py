"""Amazon Games / Prime Gaming via nile (https://github.com/imLinguin/nile), Heroic's Amazon backend.

nile isn't on PyPI and its package build is broken on current setuptools, so unless a
`nile` binary is on PATH we keep a source checkout of a pinned release and run it with uv.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser
from pathlib import Path

from .. import config
from ..matching import Ownership

NILE_REPO = "https://github.com/imLinguin/nile"
NILE_VERSION = "v1.2.0"
CHECKOUT = config.HOME / "tools" / f"nile-{NILE_VERSION}"


def _nile() -> tuple[list[str], Path | None]:
    """Command to run nile, and the directory to run it from."""
    if shutil.which("nile"):
        return ["nile"], None
    if not (shutil.which("uv") and shutil.which("git")):
        raise SystemExit("Need `nile`, or both `uv` and `git`, on PATH for Amazon support.")
    if not CHECKOUT.exists():
        print(f"Fetching nile {NILE_VERSION} into {CHECKOUT} ...")
        subprocess.run(
            ["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1",
             "--branch", NILE_VERSION, NILE_REPO, str(CHECKOUT)],
            check=True,
        )
    cmd = ["uv", "run", "--quiet", "--no-project", "--with-requirements", "requirements.txt",
           "python", "-m", "nile.cli"]
    return cmd, CHECKOUT


def _config_dir() -> Path:
    # Mirrors nile's constants.CONFIG_PATH: env overrides, then platformdirs' roaming config dir.
    if path := os.environ.get("NILE_CONFIG_PATH") or os.environ.get("XDG_CONFIG_HOME"):
        return Path(path) / "nile"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "nile"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "nile"
    return Path.home() / ".config" / "nile"


def is_configured() -> bool:
    return (_config_dir() / "current_user.json").exists()


def _read_redirect() -> str:
    # macOS terminals silently drop pasted lines over 1024 bytes, Enter included, and
    # Amazon's redirect URL is longer, so on macOS read it from the clipboard instead.
    # Linux (4096) and Windows terminals take the paste fine.
    if sys.platform == "darwin":
        print("then copy the full URL from the address bar (Cmd+L, Cmd+C). Don't paste it here.\n")
        input("Press Enter here once the URL is copied... ")
        return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
    print("then copy the full URL from the address bar and paste it here.\n")
    return input("Redirect URL: ").strip()


def login() -> None:
    # Not `nile auth --login`, whose plain input() prompt hangs on macOS (see _read_redirect).
    # Instead take nile's login secrets as JSON and finish with `nile register`.
    if is_configured():
        raise SystemExit("Already logged in to Amazon.")
    data = json.loads(_run("auth", "--login", "--non-interactive"))
    print("Log in to Amazon in the browser window. You will end up on amazon.com;")
    webbrowser.open(data["url"])
    redirect = _read_redirect()
    query = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    code = query.get("openid.oa2.authorization_code", [None])[0]
    if not code:
        raise SystemExit(
            "That isn't the redirect URL (no openid.oa2.authorization_code in it).\n"
            f"Got: {redirect[:80]!r}\nRun `mygames login amazon` again."
        )
    _run("register", "--code", code, "--client-id", data["client_id"],
         "--code-verifier", data["code_verifier"], "--serial", data["serial"])
    print("Saved Amazon login.")


def _run(*args: str) -> str:
    # nile logs to stderr; only stdout is the JSON payload.
    cmd, cwd = _nile()
    proc = subprocess.run(cmd + list(args), cwd=cwd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"nile failed (logged in? run: mygames login amazon)\n{proc.stderr.strip()}")
    return proc.stdout


def fetch() -> list[Ownership]:
    # `list` only reads nile's local cache, so refresh it from Amazon first.
    _run("library", "sync")
    games = {}
    for entitlement in json.loads(_run("library", "list", "--json") or "[]"):
        product = entitlement.get("product", {})
        if pid := product.get("id"):
            games.setdefault(pid, Ownership("amazon", pid, product.get("title") or pid))
    return list(games.values())
