import json
import urllib.parse
import urllib.request

USER_AGENT = "mygames/0.1"


def get_json(url: str, params: dict | None = None, headers: dict | None = None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)
