"""Activate the native Telegram indicator before processing a channel task."""

import json
import os
import sys
from urllib.request import Request, urlopen

TELEGRAM_PREFIX = "[Channel][Telegram]\n"


def inprogress(task, *, activate=None):
    if not task.startswith(TELEGRAM_PREFIX):
        return
    event = json.loads(task[len(TELEGRAM_PREFIX):])
    chat_id = event["chat_id"]
    if type(chat_id) is not int:
        raise ValueError("Invalid Telegram chat_id")
    (activate or activate_typing)({"chat_id": chat_id, "timeout": 30})


def activate_typing(payload):
    request = Request(
        "http://ggets:8000/telegram/typing",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(request, timeout=10) as response:
        result = json.load(response)
    if result.get("status") != "ok":
        raise RuntimeError("Telegram typing activation failed")


def main():
    try:
        inprogress(os.environ["TASK"])
    except Exception:
        print("Channel inprogress activation failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
