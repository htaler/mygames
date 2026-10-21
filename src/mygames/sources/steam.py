"""Steam via the official Web API. Needs an API key (https://steamcommunity.com/dev/apikey)."""

import re

from .. import config
from ..http import get_json
from ..matching import Ownership

API = "https://api.steampowered.com"


def resolve_steam_id(api_key: str, profile: str) -> str:
    """Accept a SteamID64, a vanity name, or a profile URL of either kind."""
    profile = profile.strip().rstrip("/")
    if m := re.search(r"/profiles/(\d{17})$", profile):
        return m.group(1)
    if re.fullmatch(r"\d{17}", profile):
        return profile
    vanity = profile.rsplit("/id/", 1)[-1]
    data = get_json(f"{API}/ISteamUser/ResolveVanityURL/v1/", {"key": api_key, "vanityurl": vanity})
    resp = data["response"]
    if resp.get("success") != 1:
        raise SystemExit(f"Could not resolve Steam profile {profile!r}: {resp.get('message', resp)}")
    return resp["steamid"]


def is_configured() -> bool:
    return "steam" in config.load_credentials()


def login() -> None:
    print("Get a Web API key at https://steamcommunity.com/dev/apikey (any domain name works).")
    api_key = input("Steam API key: ").strip()
    profile = input("Steam profile URL, vanity name or SteamID64: ").strip()
    steam_id = resolve_steam_id(api_key, profile)
    config.save_credentials("steam", {"api_key": api_key, "steam_id": steam_id})
    print(f"Saved. SteamID64 = {steam_id}")


def fetch() -> list[Ownership]:
    creds = config.load_credentials().get("steam")
    if not creds:
        raise SystemExit("Steam not configured. Run: mygames login steam")
    data = get_json(
        f"{API}/IPlayerService/GetOwnedGames/v1/",
        {
            "key": creds["api_key"],
            "steamid": creds["steam_id"],
            "include_appinfo": 1,
            "include_played_free_games": 1,
        },
    )
    games = data.get("response", {}).get("games")
    if not games:
        # An empty response (not an error) is what a private library looks like.
        raise SystemExit(
            "Steam returned no games. Set Profile > Edit Profile > Privacy > 'Game details' to Public."
        )
    return [
        Ownership("steam", str(g["appid"]), g.get("name") or f"app {g['appid']}", g.get("playtime_forever"))
        for g in games
    ]
