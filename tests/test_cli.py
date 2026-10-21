"""End-to-end through the CLI with store fetchers faked out; no network."""

import importlib
import sys

import pytest

from mygames.matching import Ownership


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.setenv("MYGAMES_HOME", str(tmp_path))
    from mygames import cli, config, db

    for mod in (config, db, cli):
        importlib.reload(mod)

    libraries = {
        "steam": [Ownership("steam", "292030", "The Witcher 3: Wild Hunt", 4000)],
        "gog": [
            Ownership("gog", "1207664663", "The Witcher 3: Wild Hunt - Game of the Year Edition"),
            Ownership("gog", "1", "Disco Elysium - The Final Cut"),
        ],
        "epic": [Ownership("epic", "Kinglet", "Disco Elysium - The Final Cut")],
        "amazon": [],
        "itch": [],
    }

    class Fake:
        def __init__(self, name):
            self.name = name

        def is_configured(self):
            return True

        def fetch(self):
            return libraries[self.name]

    monkeypatch.setattr(cli, "_source", Fake)

    def run(*argv):
        monkeypatch.setattr(sys, "argv", ["mygames", *argv])
        cli.main()

    run.libraries = libraries
    run.home = tmp_path
    return run


def test_find_dupes_and_report(cli, capsys, tmp_path):
    cli("sync")
    (tmp_path / "ea.csv").write_text("title,id\nMass Effect Legendary Edition,me1\nThe Witcher 3: Wild Hunt,w3\n")
    cli("import", "ea", str(tmp_path / "ea.csv"))
    capsys.readouterr()

    cli("find", "witcher")
    out = capsys.readouterr().out
    assert "owned on: steam, gog (The Witcher 3: Wild Hunt - Game of the Year Edition), ea" in out
    assert "play on:  STEAM" in out

    cli("find", "disco")
    assert "play on:  GOG" in capsys.readouterr().out

    cli("find", "mass efect")
    assert "Did you mean" in capsys.readouterr().out

    cli("dupes")
    assert "2 games owned on more than one platform." in capsys.readouterr().out

    out_file = tmp_path / "r.html"
    cli("report", "--out", str(out_file))
    html = out_file.read_text()
    assert "Mass Effect Legendary Edition" in html and "__DATA__" not in html


def test_one_failing_store_does_not_stop_others(cli, capsys, monkeypatch):
    import urllib.error

    from mygames import cli as cli_mod

    real = cli_mod._source

    class Broken:
        def is_configured(self):
            return True

        def fetch(self):
            raise urllib.error.HTTPError("https://api.steampowered.com", 403, "Forbidden", {}, None)

    monkeypatch.setattr(cli_mod, "_source", lambda n: Broken() if n == "steam" else real(n))
    with pytest.raises(SystemExit):
        cli("sync")
    out = capsys.readouterr().out
    assert "steam: FAILED: HTTP Error 403" in out
    assert "gog: 2 games" in out and "epic: 1 games" in out


def test_resync_drops_removed_games(cli, capsys):
    cli("sync")
    cli.libraries["gog"] = cli.libraries["gog"][:1]
    cli("sync", "gog")
    capsys.readouterr()
    cli("find", "disco")
    assert "owned on: epic\n" in capsys.readouterr().out


def test_aliases_apply_without_resync(cli, capsys):
    cli("sync")
    (cli.home / "aliases.toml").write_text('ignore = ["Disco Elysium"]\n[alias]\n')
    capsys.readouterr()
    cli("find", "disco")
    assert "Not owned anywhere" in capsys.readouterr().out
