import argparse
import os
from pathlib import Path

from sk_telegram.bridge import PollRequest, run_poll, run_send
from sk_telegram.config import load_local_config
from sk_telegram.state import DEFAULT_STATE_FILE
from sk_telegram.status import run_status
from sk_telegram.webhook import run_stop, run_webhook


def positive_integer(value: str) -> int:
    parsed_value = int(value)
    if parsed_value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Telegram messaging CLI")
    commands = parser.add_subparsers(dest="command", required=True)

    poll = commands.add_parser("poll", help="Print Telegram text messages as JSON")
    poll.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    poll.add_argument(
        "--timeout",
        type=positive_integer,
        default=30,
        help="Long-poll timeout in seconds",
    )
    poll.add_argument(
        "--once",
        action="store_true",
        help="Wait for one text message, print it, and exit",
    )

    send = commands.add_parser("send", help="Send a Telegram text message")
    send.add_argument("chat_id", type=int, nargs="?")
    send.add_argument("text", nargs="?")
    send.add_argument(
        "--from-env",
        action="store_true",
        help="Read chat ID from SK_TELEGRAM_CHAT_ID and text from SK_TELEGRAM_REPLY_TEXT",
    )

    commands.add_parser("status", help="Check Telegram and webhook readiness")
    commands.add_parser("start", help="Configure the Telegram webhook")
    commands.add_parser("stop", help="Remove the Telegram webhook")

    return parser


def environment_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value

    raise SystemExit(f"{name} is required")


def send_values_from_environment() -> tuple[int, str]:
    raw_chat_id = environment_value("SK_TELEGRAM_CHAT_ID")
    reply_text = environment_value("SK_TELEGRAM_REPLY_TEXT")
    try:
        chat_id = int(raw_chat_id)
    except ValueError as error:
        raise SystemExit("SK_TELEGRAM_CHAT_ID must be an integer") from error
    return chat_id, reply_text


def main() -> None:
    load_local_config()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        status = run_status(
            token=os.environ.get("SK_TELEGRAM_BOT_TOKEN", "").strip() or None,
            skiller_server_url=os.environ.get(
                "SK_TELEGRAM_SKILLER_SERVER_URL", "http://127.0.0.1:8001"
            ),
        )
        print(status.as_json())
        if not status.ok:
            raise SystemExit(1)
        return

    token = environment_value("SK_TELEGRAM_BOT_TOKEN")

    if args.command == "start":
        result = run_webhook(
            token=token,
            public_host=environment_value("SK_TELEGRAM_SKILLER_PUBLIC_HOST"),
            secret=environment_value("SK_TELEGRAM_WEBHOOK_SECRET"),
        )
        print(result.as_json())
        if not result.ok:
            raise SystemExit(1)
        return

    if args.command == "stop":
        result = run_stop(token=token)
        print(result.as_json())
        if not result.ok:
            raise SystemExit(1)
        return

    if args.command == "poll":
        request = PollRequest(
            token=token,
            state_file=args.state_file,
            timeout_seconds=args.timeout,
            once=args.once,
        )
        run_poll(request)
        return

    if args.from_env:
        if args.chat_id is not None or args.text is not None:
            parser.error("send --from-env does not accept chat_id or text")
        chat_id, text = send_values_from_environment()
    else:
        if args.chat_id is None or args.text is None:
            parser.error("send requires chat_id and text, or --from-env")
        chat_id, text = args.chat_id, args.text

    run_send(token=token, chat_id=chat_id, text=text)


if __name__ == "__main__":
    main()
