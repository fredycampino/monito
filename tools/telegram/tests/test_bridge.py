import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from sk_telegram.bridge import (
    PollRequest,
    TelegramMessage,
    TelegramPoller,
    parse_text_message,
    send_message,
)
from sk_telegram.state import load_offset


def telegram_update(update_id: int, username: str | None, text: str | None) -> SimpleNamespace:
    from_user = None
    if username is not None:
        from_user = SimpleNamespace(username=username)

    return SimpleNamespace(
        update_id=update_id,
        effective_message=SimpleNamespace(
            chat=SimpleNamespace(id=42),
            from_user=from_user,
            text=text,
        ),
    )


def test_parse_text_message_keeps_sender_and_text() -> None:
    update = telegram_update(update_id=17, username="SomeUser", text="Hello")

    message = parse_text_message(update)

    assert message == TelegramMessage(
        update_id=17,
        chat_id=42,
        sender_username="SomeUser",
        text="Hello",
    )
    assert json.loads(message.as_json()) == {
        "update_id": 17,
        "message": {
            "chat": {"id": 42},
            "from": {"username": "SomeUser"},
            "text": "Hello",
        },
    }


def test_emit_updates_prints_text_messages_and_advances_offset(tmp_path: Path) -> None:
    output: list[str] = []
    poller = TelegramPoller(write_line=output.append)
    state_file = tmp_path / "offset"
    updates = [
        telegram_update(update_id=17, username="first", text="Hello"),
        telegram_update(update_id=18, username="second", text="Hi"),
        telegram_update(update_id=19, username="first", text=None),
    ]

    offset, emitted = poller.emit_updates(
        updates=updates,
        state_file=state_file,
        offset=None,
        once=False,
    )

    assert [json.loads(line)["message"]["text"] for line in output] == ["Hello", "Hi"]
    assert emitted is True
    assert offset == 20
    assert load_offset(state_file) == 20


def test_emit_updates_once_stops_after_first_text_without_losing_later_updates(
    tmp_path: Path,
) -> None:
    output: list[str] = []
    poller = TelegramPoller(write_line=output.append)
    state_file = tmp_path / "offset"
    updates = [
        telegram_update(update_id=17, username="first", text=None),
        telegram_update(update_id=18, username="first", text="Hello"),
        telegram_update(update_id=19, username="second", text="Later"),
    ]

    offset, emitted = poller.emit_updates(
        updates=updates,
        state_file=state_file,
        offset=None,
        once=True,
    )

    assert [json.loads(line)["message"]["text"] for line in output] == ["Hello"]
    assert emitted is True
    assert offset == 19
    assert load_offset(state_file) == 19


def test_poll_once_retries_empty_batches_until_a_text_message(monkeypatch, tmp_path: Path) -> None:
    calls = 0

    class FakeBot:
        def __init__(self, token: str) -> None:
            assert token == "secret"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def get_updates(self, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return []
            return [telegram_update(update_id=17, username="user", text="Hello")]

    monkeypatch.setattr("sk_telegram.bridge.Bot", FakeBot)
    output: list[str] = []
    request = PollRequest(
        token="secret",
        state_file=tmp_path / "offset",
        timeout_seconds=30,
        once=True,
    )

    asyncio.run(TelegramPoller(write_line=output.append).poll(request))

    assert calls == 2
    assert json.loads(output[0])["message"]["text"] == "Hello"


def test_send_message_calls_telegram_bot(monkeypatch) -> None:
    sent_messages: list[tuple[int, str]] = []

    class FakeBot:
        def __init__(self, token: str) -> None:
            assert token == "secret"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback) -> None:
            return None

        async def send_message(self, chat_id: int, text: str) -> None:
            sent_messages.append((chat_id, text))

    monkeypatch.setattr("sk_telegram.bridge.Bot", FakeBot)

    asyncio.run(send_message(token="secret", chat_id=42, text="Hello"))

    assert sent_messages == [(42, "Hello")]
