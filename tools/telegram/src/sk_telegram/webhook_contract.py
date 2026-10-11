WEBHOOK = "telegram"
WEBHOOK_KEY = "inbox"
TOKEN_HEADER = "X-Telegram-Bot-Api-Secret-Token"

SKILLER_WEBHOOK_CONFIG: dict[str, object] = {
    "method": "POST",
    "auth": "token",
    "payload_source": "body_json",
    "token_header": TOKEN_HEADER,
    "enabled": True,
}
