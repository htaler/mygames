"""Locations of user data, plus loading of config, credentials and aliases.

Everything lives in one directory (default ~/.config/mygames, override with
MYGAMES_HOME) so secrets never end up next to the code.
"""

import json
import os
import tomllib
from pathlib import Path

HOME = Path(os.environ.get("MYGAMES_HOME", Path.home() / ".config" / "mygames"))
DB_PATH = HOME / "mygames.db"
CONFIG_PATH = HOME / "config.toml"
ALIASES_PATH = HOME / "aliases.toml"
CREDENTIALS_PATH = HOME / "credentials.json"

DEFAULT_PRIORITY = ["steam", "gog", "epic"]

DEFAULT_CONFIG = """\
# Order in which platforms are preferred when you own a game in several places.
# Platforms not listed rank after these, alphabetically.
priority = ["steam", "gog", "epic"]
"""

DEFAULT_ALIASES = """\
# Fix cross-store title matching here. Changes apply immediately, no re-sync needed.
#
# [alias] maps a store title to the title it should be grouped under:
#   "Witcher 3 Wild Hunt GOTY" = "The Witcher 3: Wild Hunt"
#
# ignore lists titles to hide entirely (soundtracks, tools, free junk):
#   ignore = ["Some Game Soundtrack"]

ignore = []

[alias]
"""


def ensure_home() -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG)
    if not ALIASES_PATH.exists():
        ALIASES_PATH.write_text(DEFAULT_ALIASES)


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def priority() -> list[str]:
    return _load_toml(CONFIG_PATH).get("priority", DEFAULT_PRIORITY)


def aliases() -> tuple[dict[str, str], list[str]]:
    data = _load_toml(ALIASES_PATH)
    return data.get("alias", {}), data.get("ignore", [])


def load_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {}
    return json.loads(CREDENTIALS_PATH.read_text())


def save_credentials(platform: str, value: dict) -> None:
    ensure_home()
    creds = load_credentials()
    creds[platform] = value
    CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2))
    CREDENTIALS_PATH.chmod(0o600)
