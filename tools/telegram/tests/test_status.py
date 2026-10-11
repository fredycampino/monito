import asyncio
import json
from types import SimpleNamespace

import pytest

from sk_telegram.status import (
    TelegramStatus,
    UrlCheck,
    check_url,
    inspect_skiller,
    inspect_status,
    public_health_url,
)


class FakeBot:
    def __init__(self, token: str) -> None:
        assert token == "secret"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def get_me(self):
        return SimpleNamespace(id=123, username="pepe_bot")

    async def get_webhook_info(self):
        return SimpleNamespace(
            url="https://bot.example/webhooks/telegram/inbox",
            last_error_date=None,
        )


def test_check_url_sends_monito_user_agent(monkeypatch) -> None:
    received = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return None

    def fake_urlopen(request, timeout):
        received["url"] = request.full_url
        received["user_agent"] = request.get_header("User-agent")
        received["timeout"] = timeout
        return Response()

    monkeypatch.setattr("sk_telegram.status.urlopen", fake_urlopen)

    result = check_url("https://bot.example/health")

    assert result == UrlCheck(ok=True, value="https://bot.example/health")
    assert received == {
        "url": "https://bot.example/health",
        "user_agent": "Monito-Telegram-Status/1.0",
        "timeout": 5,
    }


def test_inspect_status_reports_complete_healthy_chain(monkeypatch) -> None:
    monkeypatch.setattr("sk_telegram.status.Bot", FakeBot)
    checked_urls: list[str] = []

    def healthy(url: str) -> UrlCheck:
        checked_urls.append(url)
        return UrlCheck(ok=True, value=url)

    result = asyncio.run(
        inspect_status(
            token="secret",
            skiller_server_url="http://127.0.0.1:8001",
            url_check=healthy,
            skiller_check=lambda target: {
                "status": "ok",
                "version": "0.1.0",
                "path": "/venv/bin/skiller",
                "webhook": target,
                "run_id": "run-123",
            },
        )
    )

    assert json.loads(result.as_json()) == {
        "status": "ok",
        "bot": {"status": "ok", "id": 123, "username": "pepe_bot"},
        "telegram": {
            "status": "ok",
            "webhook": "https://bot.example/webhooks/telegram/inbox",
        },
        "skiller": {
            "status": "ok",
            "version": "0.1.0",
            "path": "/venv/bin/skiller",
            "webhook": "telegram:inbox",
            "run_id": "run-123",
        },
        "skiller_server": {
            "status": "ok",
            "local_url": "http://127.0.0.1:8001/health",
            "public_url": "https://bot.example/health",
        },
    }
    assert checked_urls == [
        "http://127.0.0.1:8001/health",
        "https://bot.example/health",
    ]


def test_historical_telegram_webhook_error_does_not_fail_current_status(monkeypatch) -> None:
    class BotWithHistoricalError(FakeBot):
        async def get_webhook_info(self):
            return SimpleNamespace(
                url="https://bot.example/webhooks/telegram/inbox",
                last_error_date=object(),
            )

    monkeypatch.setattr("sk_telegram.status.Bot", BotWithHistoricalError)

    result = asyncio.run(
        inspect_status(
            token="secret",
            skiller_server_url="http://127.0.0.1:8001",
            url_check=lambda url: UrlCheck(ok=True, value=url),
            skiller_check=lambda target: {
                "status": "ok",
                "version": "0.1.0",
                "path": "/venv/bin/skiller",
                "webhook": target,
                "run_id": "run-123",
            },
        )
    )

    assert result.telegram == {
        "status": "ok",
        "webhook": "https://bot.example/webhooks/telegram/inbox",
    }
    assert result.ok is True


def test_inspect_status_keeps_url_and_appends_failure() -> None:
    def unavailable(url: str) -> UrlCheck:
        return UrlCheck(ok=False, value=f"{url}: HTTP 404")

    result = asyncio.run(
        inspect_status(
            token=None,
            skiller_server_url="http://127.0.0.1:8001",
            url_check=unavailable,
            skiller_check=lambda target: {
                "status": "fail",
                "version": None,
                "path": None,
                "webhook": None,
                "run_id": None,
            },
        )
    )

    assert result.skiller_server == {
        "status": "fail",
        "local_url": "http://127.0.0.1:8001/health: HTTP 404",
        "public_url": None,
    }
    assert result.ok is False


def test_inspect_skiller_reports_version_path_and_registered_webhook(monkeypatch) -> None:
    outputs = iter(
        [
            SimpleNamespace(stdout="skiller 0.1.0b38\n"),
            SimpleNamespace(
                stdout=(
                    '[{"webhook":"telegram","method":"POST","auth":"token",'
                    '"payload_source":"body_json",'
                    '"token_header":"X-Telegram-Bot-Api-Secret-Token",'
                    '"enabled":true}]'
                )
            ),
            SimpleNamespace(
                stdout=(
                    '[{"id":"run-123","status":"WAITING",'
                    '"wait_type":"webhook","wait_detail":"telegram:inbox"}]'
                )
            ),
        ]
    )
    monkeypatch.setattr("sk_telegram.status.skiller_executable", lambda: "/bin/skiller")
    monkeypatch.setattr("sk_telegram.status.subprocess.run", lambda *args, **kwargs: next(outputs))

    assert inspect_skiller("telegram:inbox") == {
        "status": "ok",
        "version": "0.1.0b38",
        "path": "/bin/skiller",
        "webhook": "telegram:inbox",
        "run_id": "run-123",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("method", "GET"),
        ("auth", "none"),
        ("payload_source", "query"),
        ("token_header", "Other-Header"),
        ("enabled", False),
    ],
)
def test_inspect_skiller_rejects_incompatible_registration(
    monkeypatch, field: str, value: object
) -> None:
    registration = {
        "webhook": "telegram",
        "method": "POST",
        "auth": "token",
        "payload_source": "body_json",
        "token_header": "X-Telegram-Bot-Api-Secret-Token",
        "enabled": True,
    }
    registration[field] = value
    outputs = iter(
        [
            SimpleNamespace(stdout="skiller 0.1.0b38\n"),
            SimpleNamespace(stdout=json.dumps([registration])),
            SimpleNamespace(
                stdout=(
                    '[{"id":"run-123","status":"WAITING",'
                    '"wait_type":"webhook","wait_detail":"telegram:inbox"}]'
                )
            ),
        ]
    )
    monkeypatch.setattr("sk_telegram.status.skiller_executable", lambda: "/bin/skiller")
    monkeypatch.setattr("sk_telegram.status.subprocess.run", lambda *args, **kwargs: next(outputs))

    result = inspect_skiller("telegram:inbox")

    assert result["status"] == "fail"
    assert result["webhook"] is None


def test_inspect_skiller_fails_without_waiting_telegram_run(monkeypatch) -> None:
    outputs = iter(
        [
            SimpleNamespace(stdout="skiller 0.1.0b38\n"),
            SimpleNamespace(
                stdout=(
                    '[{"webhook":"telegram","method":"POST","auth":"token",'
                    '"payload_source":"body_json",'
                    '"token_header":"X-Telegram-Bot-Api-Secret-Token",'
                    '"enabled":true}]'
                )
            ),
            SimpleNamespace(stdout="[]"),
        ]
    )
    monkeypatch.setattr("sk_telegram.status.skiller_executable", lambda: "/bin/skiller")
    monkeypatch.setattr("sk_telegram.status.subprocess.run", lambda *args, **kwargs: next(outputs))

    assert inspect_skiller("telegram:inbox") == {
        "status": "fail",
        "version": "0.1.0b38",
        "path": "/bin/skiller",
        "webhook": "telegram:inbox",
        "run_id": None,
    }


def test_inspect_skiller_rejects_unexpected_webhook_key(monkeypatch) -> None:
    outputs = iter(
        [
            SimpleNamespace(stdout="skiller 0.1.0b38\n"),
            SimpleNamespace(stdout='[{"webhook":"telegram","enabled":true}]'),
            SimpleNamespace(
                stdout=(
                    '[{"id":"run-123","status":"WAITING",'
                    '"wait_type":"webhook","wait_detail":"telegram:inbox"}]'
                )
            ),
        ]
    )
    monkeypatch.setattr("sk_telegram.status.skiller_executable", lambda: "/bin/skiller")
    monkeypatch.setattr("sk_telegram.status.subprocess.run", lambda *args, **kwargs: next(outputs))

    assert inspect_skiller("telegram:other-key") == {
        "status": "fail",
        "version": "0.1.0b38",
        "path": "/bin/skiller",
        "webhook": None,
        "run_id": "run-123",
    }


def test_public_health_url_requires_https_webhook() -> None:
    assert public_health_url("https://bot.example/webhooks/telegram") == (
        "https://bot.example/health"
    )
    assert public_health_url("http://bot.example/webhooks/telegram") is None
    assert public_health_url("not-a-url") is None


def test_status_is_not_ok_when_one_section_fails() -> None:
    result = TelegramStatus(
        bot={"status": "ok", "id": 123, "username": "pepe_bot"},
        telegram={"status": "ok", "webhook": "https://bot.example"},
        skiller={
            "status": "ok",
            "version": "0.1.0",
            "path": "/bin/skiller",
            "webhook": "telegram:inbox",
            "run_id": "run-123",
        },
        skiller_server={
            "status": "fail",
            "local_url": "http://localhost: HTTP 404",
            "public_url": "https://bot.example: HTTP 404",
        },
    )

    assert json.loads(result.as_json())["status"] == "error"
