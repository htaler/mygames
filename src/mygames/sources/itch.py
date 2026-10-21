"""itch.io via the official server-side API (https://itch.io/docs/api/serverside).

Needs an API key from https://itch.io/user/settings/api-keys.
"""

from .. import config
from ..http import get_json
from ..matching import Ownership

API = "https://api.itch.io"
# Owned keys also cover asset packs, tools, soundtracks, comics and books.
GAME_CLASSIFICATIONS = {"game", "physical_game"}


def is_configured() -> bool:
    return "itch" in config.load_credentials()


def login() -> None:
    print("Create an API key at https://itch.io/user/settings/api-keys")
    api_key = input("itch.io API key: ").strip()
    profile = get_json(f"{API}/profile", headers={"Authorization": f"Bearer {api_key}"})
    config.save_credentials("itch", {"api_key": api_key})
    print(f"Saved. Logged in as {profile.get('user', {}).get('username', '?')}")


def fetch() -> list[Ownership]:
    creds = config.load_credentials().get("itch")
    if not creds:
        raise SystemExit("itch.io not configured. Run: mygames login itch")
    headers = {"Authorization": f"Bearer {creds['api_key']}"}
    games, page = {}, 1
    while True:
        data = get_json(f"{API}/profile/owned-keys", {"page": page, "per_page": 500}, headers)
        keys = data.get("owned_keys", [])
        # Pages may come back short while more follow; only an empty page means done.
        if not keys:
            break
        for key in keys:
            game = key.get("game") or {}
            if game.get("classification", "game") in GAME_CLASSIFICATIONS:
                games.setdefault(game["id"], Ownership("itch", str(game["id"]), game["title"]))
        page += 1
    return list(games.values())
