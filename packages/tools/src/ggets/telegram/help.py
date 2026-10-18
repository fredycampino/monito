"""Module-owned consumer help; never advertises provider ingress."""

OPERATIONS = ("start", "stop", "status", "send")


def describe_operations(enabled_operations):
    descriptions = {
        "start": "Register the consumer URL and activate Telegram delivery.",
        "stop": "Deactivate delivery and remove the Telegram webhook.",
        "status": "Check integration state and the registered consumer URL.",
        "send": "Send a text message to a chat.",
    }
    examples = {
        "start": {"url": "https://consumer.example/inbox"},
        "stop": {},
        "status": {},
        "send": {"chat_id": 123456789, "text": "Hello"},
    }
    return {
        "description": "Send and receive Telegram messages through GgTelegram.",
        "operations": {
            name: {
                "description": descriptions[name],
                "request": {
                    "method": "POST",
                    "path": f"/telegram/{name}",
                    "body": examples[name],
                },
            }
            for name in enabled_operations
        },
    }
