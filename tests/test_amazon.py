import json
import subprocess

import pytest

from mygames.sources import amazon

LOGIN = {"client_id": "cid", "code_verifier": "ver", "serial": "SER", "url": "https://amazon.com/ap/signin?x=1"}
REDIRECT = "https://www.amazon.com/?openid.oa2.authorization_code=ANCODE123&openid.mode=id_res&" + "x" * 1200


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setenv("NILE_CONFIG_PATH", str(tmp_path))
    calls, clipboard = [], {"text": REDIRECT}

    def run_nile(*args):
        calls.append(args)
        return json.dumps(LOGIN) if args[:2] == ("auth", "--login") else ""

    def fake_subprocess(cmd, **kw):
        assert cmd == ["pbpaste"]
        return subprocess.CompletedProcess(cmd, 0, stdout=clipboard["text"])

    monkeypatch.setattr(amazon, "_run", run_nile)
    monkeypatch.setattr(amazon.subprocess, "run", fake_subprocess)
    monkeypatch.setattr(amazon.webbrowser, "open", lambda url: None)
    monkeypatch.setattr("builtins.input", lambda prompt="": "")
    return calls, clipboard


def test_login_registers_code_from_clipboard(fake):
    calls, _ = fake
    amazon.login()
    assert calls[-1] == ("register", "--code", "ANCODE123", "--client-id", "cid",
                         "--code-verifier", "ver", "--serial", "SER")


def test_login_with_wrong_clipboard_explains(fake):
    calls, clipboard = fake
    clipboard["text"] = "https://www.amazon.com/"
    with pytest.raises(SystemExit, match="clipboard doesn't hold"):
        amazon.login()
    assert not any(c[0] == "register" for c in calls)


def test_is_configured_uses_nile_login_marker(monkeypatch, tmp_path):
    monkeypatch.setenv("NILE_CONFIG_PATH", str(tmp_path))
    assert not amazon.is_configured()
    (tmp_path / "nile").mkdir()
    (tmp_path / "nile" / "current_user.json").write_text("{}")
    assert amazon.is_configured()
