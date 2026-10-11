import json
import sys

import pytest

from sk_cloudflared import cli
from sk_cloudflared.login import LoginResult


def result(status: str = "ok") -> LoginResult:
    return LoginResult(
        status=status,
        cloudflared="/bin/cloudflared",
        authenticated=False,
        running=True,
        pid=42,
        state_path="/tmp/monito/login.json",
        log_path="/tmp/monito/login.log",
        cert_path="/tmp/cloudflared/cert.pem",
        message="message",
    )


def test_login_status_prints_json(monkeypatch, capsys) -> None:
    class Service:
        def status(self) -> LoginResult:
            return result()

    monkeypatch.setattr(cli, "LoginService", Service)
    monkeypatch.setattr(sys, "argv", ["sk-cloudflared", "login", "status"])

    cli.main()

    assert json.loads(capsys.readouterr().out)["pid"] == 42


def test_login_start_returns_non_zero_for_error(monkeypatch) -> None:
    class Service:
        def start(self) -> LoginResult:
            return result("error")

    monkeypatch.setattr(cli, "LoginService", Service)
    monkeypatch.setattr(sys, "argv", ["sk-cloudflared", "login", "start"])

    with pytest.raises(SystemExit, match="1"):
        cli.main()
