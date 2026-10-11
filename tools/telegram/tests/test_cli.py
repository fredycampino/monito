import json
import sys

import pytest

from sk_telegram import cli
from sk_telegram.bridge import PollRequest
from sk_telegram.status import TelegramStatus
from sk_telegram.webhook import WebhookResult


def test_poll_builds_request_from_environment(monkeypatch, tmp_path) -> None:
    requests: list[PollRequest] = []
    state_file = tmp_path / "offset"
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", " secret ")
    monkeypatch.setattr(cli, "run_poll", requests.append)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sk-telegram",
            "poll",
            "--once",
            "--timeout",
            "5",
            "--state-file",
            str(state_file),
        ],
    )

    cli.main()

    assert requests == [
        PollRequest(
            token="secret",
            state_file=state_file,
            timeout_seconds=5,
            once=True,
        )
    ]


def test_send_requires_token(monkeypatch) -> None:
    sent_messages: list[tuple[str, int, str]] = []
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setattr(
        cli,
        "run_send",
        lambda token, chat_id, text: sent_messages.append((token, chat_id, text)),
    )
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "send", "42", "Hello"])

    cli.main()

    assert sent_messages == [("secret", 42, "Hello")]


def test_send_from_environment_uses_chat_id(monkeypatch) -> None:
    sent_messages: list[tuple[str, int, str]] = []
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("SK_TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("SK_TELEGRAM_REPLY_TEXT", 'Reply with "quotes"')
    monkeypatch.setattr(
        cli,
        "run_send",
        lambda token, chat_id, text: sent_messages.append((token, chat_id, text)),
    )
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "send", "--from-env"])

    cli.main()

    assert sent_messages == [("secret", 42, 'Reply with "quotes"')]


def test_send_from_environment_rejects_invalid_chat_id(monkeypatch) -> None:
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("SK_TELEGRAM_CHAT_ID", "not-a-number")
    monkeypatch.setenv("SK_TELEGRAM_REPLY_TEXT", "Reply")
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "send", "--from-env"])

    with pytest.raises(SystemExit, match="SK_TELEGRAM_CHAT_ID must be an integer"):
        cli.main()


def test_status_prints_json_and_returns_non_zero_when_not_ready(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", "secret")
    monkeypatch.setenv("SK_TELEGRAM_SKILLER_SERVER_URL", "http://localhost:9000")
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "status"])
    monkeypatch.setattr(
        cli,
        "run_status",
        lambda token, skiller_server_url: TelegramStatus(
            bot={"status": "fail", "id": None, "username": None},
            telegram={"status": "fail", "webhook": None},
            skiller={
                "status": "fail",
                "version": None,
                "path": None,
                "webhook": None,
            },
            skiller_server={
                "status": "fail",
                "local_url": "http://localhost:9000/health: Connection refused",
                "public_url": None,
            },
        ),
    )

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "error",
        "bot": {"status": "fail", "id": None, "username": None},
        "telegram": {"status": "fail", "webhook": None},
        "skiller": {
            "status": "fail",
            "version": None,
            "path": None,
            "webhook": None,
        },
        "skiller_server": {
            "status": "fail",
            "local_url": "http://localhost:9000/health: Connection refused",
            "public_url": None,
        },
    }


def test_start_uses_environment_and_prints_result(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, str]] = []
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setenv("SK_TELEGRAM_SKILLER_PUBLIC_HOST", "https://host.example")
    monkeypatch.setenv("SK_TELEGRAM_WEBHOOK_SECRET", "webhook-secret")
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "start"])
    monkeypatch.setattr(
        cli,
        "run_webhook",
        lambda token, public_host, secret: (
            calls.append((token, public_host, secret))
            or WebhookResult(
                skiller={"status": "ok", "webhook": "telegram:inbox"},
                telegram={
                    "status": "ok",
                    "webhook": "https://host.example/webhooks/telegram/inbox",
                },
            )
        ),
    )

    cli.main()

    assert calls == [("bot-token", "https://host.example", "webhook-secret")]
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_stop_uses_token_and_prints_result(monkeypatch, capsys) -> None:
    calls: list[str] = []
    monkeypatch.setenv("SK_TELEGRAM_BOT_TOKEN", "bot-token")
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "stop"])
    monkeypatch.setattr(
        cli,
        "run_stop",
        lambda token: (
            calls.append(token)
            or WebhookResult(
                skiller={"status": "ok", "webhook": None},
                telegram={"status": "ok", "webhook": None},
            )
        ),
    )

    cli.main()

    assert calls == ["bot-token"]
    assert json.loads(capsys.readouterr().out) == {
        "status": "ok",
        "skiller": {"status": "ok", "webhook": None},
        "telegram": {"status": "ok", "webhook": None},
    }


def test_poll_rejects_non_positive_timeout() -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["poll", "--timeout", "0"])


def test_poll_requires_token(monkeypatch) -> None:
    monkeypatch.delenv("SK_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["sk-telegram", "poll", "--once"])

    with pytest.raises(SystemExit, match="SK_TELEGRAM_BOT_TOKEN is required"):
        cli.main()
