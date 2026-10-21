from mygames.sources import itch


def key(game_id, title, classification="game"):
    return {"id": game_id * 10, "game_id": game_id,
            "game": {"id": game_id, "title": title, "classification": classification}}


def test_fetch_pages_until_empty_and_keeps_only_games(monkeypatch):
    pages = {
        1: [key(1, "Celeste Classic"), key(2, "Pixel Asset Pack", "assets")],
        # A short page doesn't mean the end; itch says to stop only on an empty page.
        2: [key(3, "A Short Hike"), key(1, "Celeste Classic"), key(4, "OST", "soundtrack")],
        3: [],
    }
    seen = []

    def fake_get_json(url, params=None, headers=None):
        assert url.endswith("/profile/owned-keys")
        assert headers == {"Authorization": "Bearer KEY"}
        seen.append(params["page"])
        return {"page": params["page"], "per_page": 500, "owned_keys": pages[params["page"]]}

    monkeypatch.setattr(itch, "get_json", fake_get_json)
    monkeypatch.setattr(itch.config, "load_credentials", lambda: {"itch": {"api_key": "KEY"}})

    games = itch.fetch()
    assert seen == [1, 2, 3]
    assert sorted(g.title for g in games) == ["A Short Hike", "Celeste Classic"]
    assert all(g.platform == "itch" for g in games)
