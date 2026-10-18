"""Authenticated text update normalization."""

from hmac import compare_digest


class IncomingUpdateService:
    def __init__(self, secret):
        if not isinstance(secret, str) or not secret:
            raise ValueError("Missing webhook secret")
        self._secret = secret

    def process(self, update, secret_token):
        if not isinstance(secret_token, str) or not compare_digest(
            self._secret.encode(), secret_token.encode()
        ):
            raise PermissionError("Invalid webhook authentication")
        if not isinstance(update, dict) or type(update.get("update_id")) is not int:
            raise ValueError("Invalid Telegram update")
        message = update.get("message")
        if not isinstance(message, dict) or "text" not in message:
            return None
        chat = message.get("chat", {})
        sender = message.get("from", {})
        if (
            not isinstance(chat, dict)
            or type(chat.get("id")) is not int
            or type(message.get("message_id")) is not int
            or not isinstance(message["text"], str)
            or not isinstance(sender, dict)
        ):
            raise ValueError("Invalid Telegram message")
        return {
            "event_id": str(update["update_id"]),
            "type": "message",
            "chat_id": chat["id"],
            "message_id": message["message_id"],
            "sender": {"id": sender.get("id"), "name": sender.get("first_name")},
            "text": message["text"],
        }
