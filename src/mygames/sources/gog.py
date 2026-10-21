"""GOG via the same OAuth client GOG Galaxy uses (constants from heroic-gogdl's auth.py)."""

import time
import urllib.parse
import webbrowser

from .. import config
from ..http import get_json
from ..matching import Ownership

CLIENT_ID = "46899977096215655"
CLIENT_SECRET = "9d85c43b1482497dbbce61f6e4aa173a433796eeae2ca8c5f6129f2dc4de46d9"
REDIRECT_URI = "https://embed.gog.com/on_login_success?origin=client"
AUTH = "https://auth.gog.com"
EMBED = "https://embed.gog.com"

LOGIN_URL = f"{AUTH}/auth?" + urllib.parse.urlencode(
    {"client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI, "response_type": "code", "layout": "client2"}
)


def _token(params: dict) -> dict:
    tok = get_json(f"{AUTH}/token", {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, **params})
    tok["expires_at"] = time.time() + tok["expires_in"] - 60
    config.save_credentials("gog", tok)
    return tok


def is_configured() -> bool:
    return "gog" in config.load_credentials()


def login() -> None:
    print("Log in to GOG in the browser window. You will land on a mostly blank page;")
    print("copy its full URL (it contains ?code=...) and paste it here.\n")
    print(LOGIN_URL, "\n")
    webbrowser.open(LOGIN_URL)
    pasted = input("Redirect URL or code: ").strip()
    code = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query).get("code", [pasted])[0]
    _token({"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI})
    print("Saved GOG login.")


def _access_token() -> str:
    tok = config.load_credentials().get("gog")
    if not tok:
        raise SystemExit("GOG not configured. Run: mygames login gog")
    if time.time() >= tok.get("expires_at", 0):
        tok = _token({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
    return tok["access_token"]


def fetch() -> list[Ownership]:
    headers = {"Authorization": f"Bearer {_access_token()}"}
    games = {}
    # Hidden library entries are only returned with hiddenFlag=1, and they're still owned.
    for hidden in (0, 1):
        page, total = 1, 1
        while page <= total:
            # mediaType=1 is games (2 would be movies).
            params = {"mediaType": 1, "hiddenFlag": hidden, "page": page}
            data = get_json(f"{EMBED}/account/getFilteredProducts", params, headers)
            total = data.get("totalPages", 1)
            for p in data.get("products", []):
                games.setdefault(p["id"], Ownership("gog", str(p["id"]), p["title"]))
            page += 1
    return list(games.values())
