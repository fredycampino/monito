import asyncio
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from telegram import Bot, Update

from sk_telegram.state import load_offset, save_offset


@dataclass(frozen=True)
class TelegramMessage:
    update_id: int
    chat_id: int
    sender_username: str | None
    text: str

    def as_json(self) -> str:
        payload = {
            "update_id": self.update_id,
            "message": {
                "chat": {"id": self.chat_id},
                "from": {"username": self.sender_username},
                "text": self.text,
            },
        }
        return json.dumps(payload, ensure_ascii=False)


@dataclass(frozen=True)
class PollRequest:
    token: str
    state_file: Path
    timeout_seconds: int
    once: bool


def parse_text_message(update: Update) -> TelegramMessage | None:
    message = update.effective_message
    if message is None or message.text is None:
        return None

    sender_username = None
    if message.from_user is not None:
        sender_username = message.from_user.username

    return TelegramMessage(
        update_id=update.update_id,
        chat_id=message.chat.id,
        sender_username=sender_username,
        text=message.text,
    )


def print_line(line: str) -> None:
    print(line, flush=True)


class TelegramPoller:
    def __init__(self, write_line: Callable[[str], None] = print_line) -> None:
        self._write_line = write_line

    async def poll(self, request: PollRequest) -> None:
        offset = load_offset(request.state_file)

        async with Bot(token=request.token) as bot:
            while True:
                updates = await bot.get_updates(
                    offset=offset,
                    timeout=request.timeout_seconds,
                    read_timeout=request.timeout_seconds + 5,
                    allowed_updates=["message"],
                )
                offset, message_emitted = self.emit_updates(
                    updates=updates,
                    state_file=request.state_file,
                    offset=offset,
                    once=request.once,
                )
                if request.once and message_emitted:
                    return

    def emit_updates(
        self,
        updates: Sequence[Update],
        state_file: Path,
        offset: int | None,
        once: bool,
    ) -> tuple[int | None, bool]:
        next_offset = offset
        message_emitted = False
        for update in updates:
            message = parse_text_message(update)
            next_offset = update.update_id + 1

            if message is None:
                save_offset(state_file=state_file, offset=next_offset)
                continue

            self._write_line(message.as_json())
            save_offset(state_file=state_file, offset=next_offset)
            message_emitted = True
            if once:
                return next_offset, True

        return next_offset, message_emitted


def run_poll(request: PollRequest) -> None:
    poller = TelegramPoller()
    asyncio.run(poller.poll(request))


async def send_message(token: str, chat_id: int, text: str) -> None:
    async with Bot(token=token) as bot:
        await bot.send_message(chat_id=chat_id, text=text)


def run_send(token: str, chat_id: int, text: str) -> None:
    asyncio.run(send_message(token=token, chat_id=chat_id, text=text))
