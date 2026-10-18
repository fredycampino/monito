"""Consumer facade coordinating business services."""

import re
from pathlib import Path
from threading import RLock

import httpx
from ggets.telegram.adapters import SubscriptionStore, TelegramClient
from ggets.telegram.business.delivery import DeliveryService
from ggets.telegram.business.incoming_update import IncomingUpdateService
from ggets.telegram.business.message import MessageService
from ggets.telegram.business.subscription import ConsumerSubscriptionService
from ggets.telegram.business.webhook import TelegramWebhookService
from ggets.telegram.config import ConfigurationError
from ggets.telegram.schemas import OperationResult


class TelegramService:
    def __init__(self, config, client=None, store=None, transport=None):
        self.config = config
        self.client = client if client is not None else TelegramClient(config)
        self.subscription = ConsumerSubscriptionService(
            store if store is not None else SubscriptionStore(config.state_file)
        )
        self.messages = MessageService(self.client)
        self.delivery = DeliveryService(
            transport if transport is not None else httpx, config.request_timeout_seconds
        )
        self.lock = RLock()

    def secret(self):
        self.config.require_configured()
        try:
            secret = Path(self.config.webhook_secret_file).read_text().strip()
        except OSError:
            raise ConfigurationError("Cannot read Telegram webhook secret") from None
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret):
            raise ConfigurationError("Invalid Telegram webhook secret")
        return secret

    def webhook(self):
        return TelegramWebhookService(self.client, self.config.webhook_url, self.secret())

    def start(self, request):
        webhook = self.webhook()
        with self.lock:
            previous = self.subscription.status()
            self.subscription.activate(str(request.url))
            try:
                webhook.register()
            except Exception:
                self.subscription.store.save(previous)
                raise
            return OperationResult(status="ok", data=self.subscription.status())

    def stop(self, request):
        with self.lock:
            self.webhook().unregister()
            self.subscription.deactivate()
            return OperationResult(status="ok", data=self.subscription.status())

    def status(self, request):
        missing = self.config.missing_fields()
        if missing:
            return OperationResult(status="not_configured", data={"missing_fields": missing})
        with self.lock:
            return OperationResult(
                status="ok",
                data={
                    "subscription": self.subscription.status(),
                    "webhook": self.webhook().status(),
                },
            )

    def send(self, request):
        self.config.require_configured()
        return OperationResult(status="ok", data=self.messages.send(request))

    def receive_update(self, update, secret_token):
        event = IncomingUpdateService(self.secret()).process(update, secret_token)
        if event is None:
            return {"status": "ignored"}
        with self.lock:
            subscription = self.subscription.status()
            if not subscription["active"]:
                raise RuntimeError("Consumer is inactive")
            self.delivery.deliver(subscription["url"], event)
        return {"status": "ok"}
