"""Module-owned configuration; no secret files are read during assembly."""

from dataclasses import dataclass, field, replace
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    """Missing or unusable module configuration."""


@dataclass(frozen=True)
class Config:
    base_url: str | None
    webhook: str
    bot_father_token_file: str | None = field(repr=False)
    webhook_secret_file: str | None
    state_file: str
    request_timeout_seconds: int

    receiver_host: str
    receiver_port: int

    def missing_fields(self):
        return [
            name
            for name in ("base_url", "bot_father_token_file", "webhook_secret_file")
            if getattr(self, name) is None
        ]

    def require_configured(self):
        missing = self.missing_fields()
        if missing:
            raise ConfigurationError("Missing Telegram configuration: " + ", ".join(missing))

    @property
    def webhook_url(self):
        self.require_configured()
        return self.base_url + self.webhook


DEFAULT_CONFIG = Config(
    base_url=None,
    webhook="/telegram/webhook",
    bot_father_token_file=None,
    webhook_secret_file=None,
    state_file="/data/telegram/state.json",
    request_timeout_seconds=10,
    receiver_host="127.0.0.1",
    receiver_port=8001,
)


def valid_base_url(value):
    if not isinstance(value, str) or any(char.isspace() for char in value):
        return False
    try:
        url = urlsplit(value)
        return (
            url.scheme == "https"
            and bool(url.hostname)
            and url.port != 0
            and url.username is None
            and url.password is None
            and url.path in ("", "/")
            and not url.query
            and not url.fragment
        )
    except ValueError:
        return False


def map_config(value: dict[str, object]) -> Config:
    values = {}
    base_url = value.get("base_url")
    if valid_base_url(base_url):
        values["base_url"] = base_url.rstrip("/")
    webhook = value.get("webhook")
    if (
        isinstance(webhook, str)
        and webhook.startswith("/telegram/")
        and not any(char.isspace() for char in webhook)
        and not any(char in webhook for char in "?#{}")
        and all(part not in ("", ".", "..") for part in webhook.split("/")[1:])
        and webhook
        not in {
            "/telegram/help",
            "/telegram/start",
            "/telegram/stop",
            "/telegram/status",
            "/telegram/send",
            "/telegram/typing",
        }
    ):
        values["webhook"] = webhook
    for name in ("bot_father_token_file", "webhook_secret_file", "state_file"):
        item = value.get(name)
        if isinstance(item, str) and item.strip():
            values[name] = item.strip()
    timeout = value.get("request_timeout_seconds")
    if type(timeout) is int and timeout > 0:
        values["request_timeout_seconds"] = timeout
    host, port = value.get("receiver_host"), value.get("receiver_port")
    if isinstance(host, str) and host.strip():
        values["receiver_host"] = host.strip()
    if type(port) is int and 1 <= port <= 65535:
        values["receiver_port"] = port
    return replace(DEFAULT_CONFIG, **values)
