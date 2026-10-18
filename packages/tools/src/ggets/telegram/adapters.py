"""HTTP and atomic storage adapters; construction has no external effects."""

import json
import os
import tempfile
from pathlib import Path

import httpx
from ggets.telegram.config import ConfigurationError


class TelegramClient:
    def __init__(self, config):
        self.config = config

    def call(self, operation, body):
        try:
            token = Path(self.config.bot_father_token_file).expanduser().read_text().strip()
            if not token or any(char.isspace() for char in token):
                raise ValueError()
        except (OSError, TypeError, ValueError):
            raise ConfigurationError("Cannot read valid Telegram bot token file") from None
        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{token}/{operation}",
                json=body,
                timeout=self.config.request_timeout_seconds,
                follow_redirects=False,
            )
            response.raise_for_status()
            value = response.json()
            if not value.get("ok"):
                raise ValueError()
            return value["result"]
        except Exception:
            raise RuntimeError("Telegram request failed") from None


class SubscriptionStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self):
        try:
            return json.loads(self.path.read_text())
        except FileNotFoundError:
            return None

    def save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.path.parent, delete=False) as file:
                name = file.name
                json.dump(state, file)
                file.flush()
                os.fsync(file.fileno())
            os.replace(name, self.path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)
