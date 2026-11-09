# Telegram configuration

JSON section: `telegram`. Paths refer to the filesystem where Ggets runs.

| Field | Required | Default | Purpose |
| --- | --- | --- | --- |
| `base_url` | Yes | — | Public HTTPS base URL, without a path, credentials or query. |
| `webhook` | No | `/telegram/webhook` | Receiver path appended to `base_url`; must be under `/telegram/` and not conflict with tool routes. |
| `bot_father_token_file` | Yes | — | File containing the BotFather token. |
| `webhook_secret_file` | Yes | — | File containing the secret used to authenticate incoming Telegram events. |
| `state_file` | No | `/data/telegram/state.json` | Persistent consumer URL and activation state. |
| `request_timeout_seconds` | No | `10` | Positive timeout for outbound requests, in seconds. |
| `receiver_host` | No | `127.0.0.1` | Receiver listen address; use the ingress interface IP in Docker. |
| `receiver_port` | No | `8001` | Receiver listen port, from 1 to 65535. |

Invalid values fall back to defaults. Missing required fields produce `not_configured` in `status` and block actions. The receiver starts only when all required fields are set and its secret is valid. The consumer URL is supplied to `start`, not configured here.

## Minimal JSON (required fields only)

```json
{
  "telegram": {
    "base_url": "https://bot.example.com",
    "bot_father_token_file": "/run/secrets/telegram_bot_token",
    "webhook_secret_file": "/run/secrets/telegram_webhook_secret"
  }
}
```

## Effective configuration (with defaults)

```json
{
  "telegram": {
    "base_url": "https://bot.example.com",
    "bot_father_token_file": "/run/secrets/telegram_bot_token",
    "webhook_secret_file": "/run/secrets/telegram_webhook_secret",
    "webhook": "/telegram/webhook",
    "state_file": "/data/telegram/state.json",
    "request_timeout_seconds": 10,
    "receiver_host": "127.0.0.1",
    "receiver_port": 8001
  }
}
```

For Docker ingress isolation, override `receiver_host` with the configured ingress IP; the default listens only on container loopback.
