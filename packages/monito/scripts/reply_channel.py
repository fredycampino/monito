"""Deliver final Telegram replies without involving the agent in transport."""

import json
import os
import sys
from urllib.request import Request, urlopen

TELEGRAM_PREFIX = "[Channel][Telegram]\n"
SEND_URL = "http://ggets:8000/telegram/send"


def reply_channel(task, output, *, send=None):
    if not task.startswith(TELEGRAM_PREFIX):
        return
    data = output["data"]
    if data.get("stop_reason") != "final" or not data.get("final"):
        return
    event = json.loads(task[len(TELEGRAM_PREFIX):])
    chat_id = event["chat_id"]
    if type(chat_id) is not int:
        raise ValueError("Invalid Telegram chat_id")
    text = data["final"]
    send = send or send_telegram
    for start in range(0, len(text), 4096):
        send({"chat_id": chat_id, "text": text[start:start + 4096]})


def send_telegram(payload):
    request = Request(
        SEND_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=10) as response:
        result = json.load(response)
    if result.get("status") != "ok":
        raise RuntimeError("Telegram delivery failed")


def main():
    try:
        reply_channel(os.environ["TASK"], json.loads(os.environ["AGENT_OUTPUT"]))
    except Exception:
        # Never expose the payload, reply, or upstream error in Runtime logs.
        print("Channel reply delivery failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
