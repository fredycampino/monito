import asyncio
import json
import subprocess
from dataclasses import dataclass
from urllib.parse import urlsplit

from telegram import Bot

from sk_telegram.config import skiller_executable
from sk_telegram.webhook_contract import (
    SKILLER_WEBHOOK_CONFIG,
    TOKEN_HEADER,
    WEBHOOK,
    WEBHOOK_KEY,
)


@dataclass(frozen=True)
class WebhookResult:
    skiller: dict[str, object]
    telegram: dict[str, object]

    @property
    def ok(self) -> bool:
        return self.skiller["status"] == "ok" and self.telegram["status"] == "ok"

    def as_json(self) -> str:
        return json.dumps(
            {
                "status": "ok" if self.ok else "error",
                "skiller": self.skiller,
                "telegram": self.telegram,
            },
            ensure_ascii=False,
        )


def webhook_url(public_host: str) -> str:
    host = public_host.rstrip("/")
    parsed = urlsplit(host)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("SK_TELEGRAM_SKILLER_PUBLIC_HOST must be an HTTPS origin")
    return f"{host}/webhooks/{WEBHOOK}/{WEBHOOK_KEY}"


def _run_skiller(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    executable = skiller_executable()
    if executable is None:
        raise RuntimeError("skiller is not installed")
    return subprocess.run(
        [executable, *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )


def configure_skiller(secret: str) -> dict[str, object]:
    try:
        registrations = json.loads(_run_skiller(["webhook", "list"]).stdout)
        existing = next(
            (
                item
                for item in registrations
                if isinstance(item, dict) and item.get("webhook") == WEBHOOK
            ),
            None,
        )
        matches = existing is not None and all(
            existing.get(key) == value for key, value in SKILLER_WEBHOOK_CONFIG.items()
        )
        if existing is not None and not matches:
            _run_skiller(["webhook", "remove", WEBHOOK])
            existing = None
        if existing is None:
            _run_skiller(
                [
                    "webhook",
                    "register",
                    WEBHOOK,
                    "--auth",
                    "token",
                    "--token-header",
                    TOKEN_HEADER,
                ]
            )
        _run_skiller(
            [
                "webhook",
                "secret",
                WEBHOOK,
                "--secret-env",
                "SK_TELEGRAM_WEBHOOK_SECRET",
            ]
        )
        return {"status": "ok", "webhook": f"{WEBHOOK}:{WEBHOOK_KEY}"}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError) as error:
        return {
            "status": "fail",
            "webhook": f"{WEBHOOK}:{WEBHOOK_KEY}: {type(error).__name__}: {error}",
        }


async def configure_telegram(token: str, url: str, secret: str) -> dict[str, object]:
    try:
        async with Bot(token=token) as bot:
            configured = await bot.set_webhook(
                url=url,
                secret_token=secret,
                allowed_updates=["message"],
            )
        if not configured:
            return {"status": "fail", "webhook": f"{url}: rejected by Telegram"}
        return {"status": "ok", "webhook": url}
    except Exception as error:
        return {
            "status": "fail",
            "webhook": f"{url}: {type(error).__name__}: {error}",
        }


async def configure_webhook(token: str, public_host: str, secret: str) -> WebhookResult:
    try:
        url = webhook_url(public_host)
    except ValueError as error:
        return WebhookResult(
            skiller={"status": "fail", "webhook": f"{WEBHOOK}:{WEBHOOK_KEY}: not configured"},
            telegram={"status": "fail", "webhook": str(error)},
        )

    skiller = configure_skiller(secret)
    telegram = (
        await configure_telegram(token, url, secret)
        if skiller["status"] == "ok"
        else {"status": "fail", "webhook": f"{url}: not configured"}
    )
    return WebhookResult(skiller=skiller, telegram=telegram)


def run_webhook(token: str, public_host: str, secret: str) -> WebhookResult:
    return asyncio.run(configure_webhook(token, public_host, secret))


def remove_skiller_webhook() -> dict[str, object]:
    try:
        registrations = json.loads(_run_skiller(["webhook", "list"]).stdout)
        registered = any(
            isinstance(item, dict) and item.get("webhook") == WEBHOOK for item in registrations
        )
        if registered:
            _run_skiller(["webhook", "remove", WEBHOOK])
        return {"status": "ok", "webhook": None}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, RuntimeError) as error:
        return {
            "status": "fail",
            "webhook": f"{WEBHOOK}:{WEBHOOK_KEY}: {type(error).__name__}: {error}",
        }


async def remove_telegram_webhook(token: str) -> dict[str, object]:
    try:
        async with Bot(token=token) as bot:
            removed = await bot.delete_webhook()
        if not removed:
            return {"status": "fail", "webhook": "rejected by Telegram"}
        return {"status": "ok", "webhook": None}
    except Exception as error:
        return {
            "status": "fail",
            "webhook": f"{type(error).__name__}: {error}",
        }


async def remove_webhook(token: str) -> WebhookResult:
    telegram = await remove_telegram_webhook(token)
    skiller = (
        remove_skiller_webhook()
        if telegram["status"] == "ok"
        else {"status": "fail", "webhook": f"{WEBHOOK}:{WEBHOOK_KEY}: not removed"}
    )
    return WebhookResult(skiller=skiller, telegram=telegram)


def run_stop(token: str) -> WebhookResult:
    return asyncio.run(remove_webhook(token))
