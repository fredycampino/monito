import asyncio
import json
from types import SimpleNamespace

import pytest

from sk_telegram.webhook import (
    WebhookResult,
    configure_skiller,
    configure_telegram,
    remove_skiller_webhook,
    remove_telegram_webhook,
    remove_webhook,
    webhook_url,
)


def test_webhook_url_builds_fixed_telegram_endpoint() -> None:
    assert webhook_url("https://skiller.example") == (
        "https://skiller.example/webhooks/telegram/inbox"
    )


@pytest.mark.parametrize(
    "public_host",
    [
        "https://skiller.example?source=test",
        "https://skiller.example#fragment",
    ],
)
def test_webhook_url_rejects_query_and_fragment(public_host: str) -> None:
    with pytest.raises(ValueError, match="must be an HTTPS origin"):
        webhook_url(public_host)


def test_configure_skiller_registers_expected_webhook(monkeypatch) -> None:
    calls: list[list[str]] = []

    def run(arguments: list[str]):
        calls.append(arguments)
        if arguments == ["webhook", "list"]:
            return SimpleNamespace(stdout="[]")
        return SimpleNamespace(stdout='{"status":"REGISTERED"}')

    monkeypatch.setattr("sk_telegram.webhook._run_skiller", run)

    assert configure_skiller("provided-secret") == {
        "status": "ok",
        "webhook": "telegram:inbox",
    }
    assert calls == [
        ["webhook", "list"],
        [
            "webhook",
            "register",
            "telegram",
            "--auth",
            "token",
            "--token-header",
            "X-Telegram-Bot-Api-Secret-Token",
        ],
        [
            "webhook",
            "secret",
            "telegram",
            "--secret-env",
            "SK_TELEGRAM_WEBHOOK_SECRET",
        ],
    ]


def test_configure_skiller_is_idempotent(monkeypatch) -> None:
    calls: list[list[str]] = []
    registration = {
        "webhook": "telegram",
        "secret": "provided-secret",
        "method": "POST",
        "auth": "token",
        "payload_source": "body_json",
        "token_header": "X-Telegram-Bot-Api-Secret-Token",
        "enabled": True,
    }

    def run(arguments: list[str]):
        calls.append(arguments)
        return SimpleNamespace(stdout=json.dumps([registration]))

    monkeypatch.setattr("sk_telegram.webhook._run_skiller", run)

    assert configure_skiller("provided-secret")["status"] == "ok"
    assert calls == [
        ["webhook", "list"],
        [
            "webhook",
            "secret",
            "telegram",
            "--secret-env",
            "SK_TELEGRAM_WEBHOOK_SECRET",
        ],
    ]


def test_configure_telegram_sets_url_and_secret(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class FakeBot:
        def __init__(self, token: str) -> None:
            assert token == "bot-token"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def set_webhook(
            self,
            *,
            url: str,
            secret_token: str,
            allowed_updates: list[str],
        ) -> bool:
            assert allowed_updates == ["message"]
            calls.append((url, secret_token))
            return True

    monkeypatch.setattr("sk_telegram.webhook.Bot", FakeBot)
    result = asyncio.run(
        configure_telegram("bot-token", "https://host/webhooks/telegram/inbox", "secret")
    )

    assert result == {
        "status": "ok",
        "webhook": "https://host/webhooks/telegram/inbox",
    }
    assert calls == [("https://host/webhooks/telegram/inbox", "secret")]


def test_remove_skiller_webhook_removes_existing_registration(monkeypatch) -> None:
    calls: list[list[str]] = []

    def run(arguments: list[str]):
        calls.append(arguments)
        if arguments == ["webhook", "list"]:
            return SimpleNamespace(stdout='[{"webhook":"telegram"}]')
        return SimpleNamespace(stdout='{"status":"REMOVED"}')

    monkeypatch.setattr("sk_telegram.webhook._run_skiller", run)

    assert remove_skiller_webhook() == {"status": "ok", "webhook": None}
    assert calls == [["webhook", "list"], ["webhook", "remove", "telegram"]]


def test_remove_skiller_webhook_is_idempotent(monkeypatch) -> None:
    calls: list[list[str]] = []

    def run(arguments: list[str]):
        calls.append(arguments)
        return SimpleNamespace(stdout="[]")

    monkeypatch.setattr("sk_telegram.webhook._run_skiller", run)

    assert remove_skiller_webhook() == {"status": "ok", "webhook": None}
    assert calls == [["webhook", "list"]]


def test_remove_telegram_webhook(monkeypatch) -> None:
    calls: list[str] = []

    class FakeBot:
        def __init__(self, token: str) -> None:
            assert token == "bot-token"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def delete_webhook(self) -> bool:
            calls.append("delete_webhook")
            return True

    monkeypatch.setattr("sk_telegram.webhook.Bot", FakeBot)

    assert asyncio.run(remove_telegram_webhook("bot-token")) == {
        "status": "ok",
        "webhook": None,
    }
    assert calls == ["delete_webhook"]


def test_remove_webhook_stops_telegram_before_skiller(monkeypatch) -> None:
    calls: list[str] = []

    async def remove_telegram(token: str) -> dict[str, object]:
        calls.append(f"telegram:{token}")
        return {"status": "ok", "webhook": None}

    def remove_skiller() -> dict[str, object]:
        calls.append("skiller")
        return {"status": "ok", "webhook": None}

    monkeypatch.setattr("sk_telegram.webhook.remove_telegram_webhook", remove_telegram)
    monkeypatch.setattr("sk_telegram.webhook.remove_skiller_webhook", remove_skiller)

    result = asyncio.run(remove_webhook("bot-token"))

    assert result.ok is True
    assert calls == ["telegram:bot-token", "skiller"]


def test_remove_webhook_keeps_skiller_when_telegram_fails(monkeypatch) -> None:
    async def remove_telegram(token: str) -> dict[str, object]:
        return {"status": "fail", "webhook": "Telegram API unavailable"}

    monkeypatch.setattr("sk_telegram.webhook.remove_telegram_webhook", remove_telegram)
    monkeypatch.setattr(
        "sk_telegram.webhook.remove_skiller_webhook",
        lambda: pytest.fail("Skiller webhook must remain registered"),
    )

    result = asyncio.run(remove_webhook("bot-token"))

    assert result.ok is False
    assert result.skiller == {
        "status": "fail",
        "webhook": "telegram:inbox: not removed",
    }


def test_webhook_result_requires_both_sides() -> None:
    result = WebhookResult(
        skiller={"status": "ok", "webhook": "telegram:inbox"},
        telegram={"status": "fail", "webhook": "https://host: HTTP 400"},
    )

    assert result.ok is False
    assert json.loads(result.as_json())["status"] == "error"
