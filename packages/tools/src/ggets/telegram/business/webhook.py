"""Provider webhook lifecycle."""


class TelegramWebhookService:
    def __init__(self, client, webhook_url, secret):
        self.client = client
        self.webhook_url = webhook_url
        self._secret = secret

    def register(self):
        return self.client.call(
            "setWebhook",
            {
                "url": self.webhook_url,
                "secret_token": self._secret,
                "allowed_updates": ["message"],
                "drop_pending_updates": False,
            },
        )

    def unregister(self):
        return self.client.call("deleteWebhook", {"drop_pending_updates": False})

    def status(self):
        result = self.client.call("getWebhookInfo", {})
        return {
            "registered": result.get("url") == self.webhook_url,
            "pending_updates": result.get("pending_update_count", 0),
            "last_error_at": result.get("last_error_date"),
        }
