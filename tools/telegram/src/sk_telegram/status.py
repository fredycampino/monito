import asyncio
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from telegram import Bot

from sk_telegram.config import skiller_executable
from sk_telegram.webhook_contract import SKILLER_WEBHOOK_CONFIG, WEBHOOK, WEBHOOK_KEY

STATUS_OK = "ok"
STATUS_FAIL = "fail"


@dataclass(frozen=True)
class UrlCheck:
    ok: bool
    value: str


@dataclass(frozen=True)
class TelegramStatus:
    bot: dict[str, object]
    telegram: dict[str, object]
    skiller: dict[str, object]
    skiller_server: dict[str, object]

    @property
    def ok(self) -> bool:
        sections = (self.bot, self.telegram, self.skiller, self.skiller_server)
        return all(section["status"] == STATUS_OK for section in sections)

    def as_json(self) -> str:
        return json.dumps(
            {
                "status": STATUS_OK if self.ok else "error",
                "bot": self.bot,
                "telegram": self.telegram,
                "skiller": self.skiller,
                "skiller_server": self.skiller_server,
            },
            ensure_ascii=False,
        )


def public_health_url(webhook_url: str) -> str | None:
    parsed_url = urlsplit(webhook_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        return None
    return f"{parsed_url.scheme}://{parsed_url.netloc}/health"


def webhook_target(webhook_url: str) -> str | None:
    parts = [part for part in urlsplit(webhook_url).path.split("/") if part]
    if len(parts) >= 3 and parts[-3] == "webhooks":
        return f"{parts[-2]}:{parts[-1]}"
    return None


def inspect_skiller(target: str | None) -> dict[str, object]:
    path = skiller_executable()
    version = None
    registered_target = None
    run_id = None
    if path:
        try:
            version_result = subprocess.run(
                [path, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            version = version_result.stdout.strip().removeprefix("skiller ") or None
            registrations_result = subprocess.run(
                [path, "webhook", "list"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            registrations = json.loads(registrations_result.stdout)
            expected_target = f"{WEBHOOK}:{WEBHOOK_KEY}"
            if target == expected_target and any(
                registration.get("webhook") == WEBHOOK
                and all(
                    registration.get(key) == value for key, value in SKILLER_WEBHOOK_CONFIG.items()
                )
                for registration in registrations
                if isinstance(registration, dict)
            ):
                registered_target = target

            runs_result = subprocess.run(
                [path, "runs", "--status", "WAITING", "--limit", "100"],
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
            runs = json.loads(runs_result.stdout)
            run_id = next(
                (
                    run.get("id")
                    for run in runs
                    if isinstance(run, dict)
                    and run.get("wait_type") == "webhook"
                    and run.get("wait_detail") == expected_target
                    and isinstance(run.get("id"), str)
                ),
                None,
            )
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            pass

    return {
        "status": (STATUS_OK if path and version and registered_target and run_id else STATUS_FAIL),
        "version": version,
        "path": path,
        "webhook": registered_target,
        "run_id": run_id,
    }


def check_url(url: str) -> UrlCheck:
    request = Request(url, headers={"User-Agent": "Monito-Telegram-Status/1.0"})
    try:
        with urlopen(request, timeout=5) as response:
            if 200 <= response.status < 300:
                return UrlCheck(ok=True, value=url)
            return UrlCheck(ok=False, value=f"{url}: HTTP {response.status}")
    except HTTPError as error:
        return UrlCheck(ok=False, value=f"{url}: HTTP {error.code}")
    except URLError as error:
        reason = getattr(error.reason, "strerror", None) or str(error.reason)
        return UrlCheck(ok=False, value=f"{url}: {reason}")
    except Exception as error:
        return UrlCheck(ok=False, value=f"{url}: {type(error).__name__}: {error}")


async def inspect_status(
    token: str | None,
    skiller_server_url: str,
    url_check: Callable[[str], UrlCheck] = check_url,
    skiller_check: Callable[[str | None], dict[str, object]] = inspect_skiller,
) -> TelegramStatus:
    bot_section: dict[str, object] = {"status": STATUS_FAIL, "id": None, "username": None}
    telegram_section: dict[str, object] = {"status": STATUS_FAIL, "webhook": None}
    webhook_url = None

    if token:
        try:
            async with Bot(token=token) as bot:
                bot_user = await bot.get_me()
                bot_section = {
                    "status": STATUS_OK,
                    "id": bot_user.id,
                    "username": bot_user.username,
                }
                webhook_info = await bot.get_webhook_info()
                webhook_url = webhook_info.url or None
                telegram_section = {
                    "status": STATUS_OK if webhook_url else STATUS_FAIL,
                    "webhook": webhook_url,
                }
        except Exception as error:
            telegram_section["webhook"] = f"Telegram API: {type(error).__name__}: {error}"

    skiller_section = skiller_check(webhook_target(webhook_url) if webhook_url else None)

    local_url = f"{skiller_server_url.rstrip('/')}/health"
    local_result = url_check(local_url)
    public_url = public_health_url(webhook_url) if webhook_url else None
    public_result = url_check(public_url) if public_url else None
    skiller_server_section = {
        "status": (
            STATUS_OK
            if local_result.ok and public_result is not None and public_result.ok
            else STATUS_FAIL
        ),
        "local_url": local_result.value,
        "public_url": public_result.value if public_result else None,
    }

    return TelegramStatus(
        bot=bot_section,
        telegram=telegram_section,
        skiller=skiller_section,
        skiller_server=skiller_server_section,
    )


def run_status(
    token: str | None,
    skiller_server_url: str,
    url_check: Callable[[str], UrlCheck] = check_url,
) -> TelegramStatus:
    return asyncio.run(
        inspect_status(
            token=token,
            skiller_server_url=skiller_server_url,
            url_check=url_check,
        )
    )
