# `sk-telegram` CLI API

`sk-telegram` lets users and Skiller agents send and receive Telegram bot text messages from the command line.

## Requirements

- Python 3.11 or newer.
- A Telegram bot created with BotFather.
- The bot token provided through `SK_TELEGRAM_BOT_TOKEN`.
- Network access to the Telegram Bot API.

Never store the bot token in the repository.

## Environment

The CLI loads the nearest `.env` from the current directory or its parents. Use it only for non-secret local configuration, such as `SKILLER_BIN`. Exported environment variables take priority. Secrets must come from the system environment, CI, service configuration, or a secret manager.

| Variable | Required by | Value |
|---|---|---|
| `SKILLER_BIN` | `status`, `start`, `stop` | Skiller executable; defaults to `skiller` from `PATH` |
| `SK_TELEGRAM_BOT_TOKEN` | All commands | Telegram bot token |
| `SK_TELEGRAM_CHAT_ID` | `send --from-env` | Integer chat ID |
| `SK_TELEGRAM_REPLY_TEXT` | `send --from-env` | Message text |
| `SK_TELEGRAM_SKILLER_SERVER_URL` | `status` | Local server URL; default: `http://127.0.0.1:8001` |
| `SK_TELEGRAM_SKILLER_PUBLIC_HOST` | `start` | Public HTTPS tunnel origin |
| `SK_TELEGRAM_WEBHOOK_SECRET` | `start` | Telegram webhook secret token |

## `sk-telegram --help`

```text
sk-telegram --help
```

Prints the command help to stdout.

Return: `0`.

## `sk-telegram status`

Checks the bot, Telegram API, Skiller installation and webhook registration, and the local and public server endpoints.

```text
sk-telegram status
```

Output: one JSON object.

```json
{
  "status": "ok",
  "bot": {
    "status": "ok",
    "id": 123456,
    "username": "pepe_bot"
  },
  "telegram": {
    "status": "ok",
    "webhook": "https://bot.example/webhooks/telegram/inbox"
  },
  "skiller": {
    "status": "ok",
    "version": "0.1.0",
    "path": "/path/to/skiller",
    "webhook": "telegram:inbox",
    "run_id": "70a43be8-cdc9-46fd-94f4-73d1f6c6579d"
  },
  "skiller_server": {
    "status": "ok",
    "local_url": "http://127.0.0.1:8001/health",
    "public_url": "https://bot.example/health"
  }
}
```

Section status values: `ok` or `fail`. `skiller.run_id` identifies the run waiting for `telegram:inbox`; without one, the `skiller` section fails. A failed URL check keeps the URL and appends the result, for example `https://bot.example/health: HTTP 404`. Unavailable values are `null`.

Return: `0` when every section is `ok`; `1` otherwise.

## `sk-telegram start`

Registers `telegram:inbox` in Skiller and configures Telegram with the public endpoint and secret token.

```text
sk-telegram start
```

Output: one JSON object.

```json
{
  "status": "ok",
  "skiller": {"status": "ok", "webhook": "telegram:inbox"},
  "telegram": {
    "status": "ok",
    "webhook": "https://skiller.example/webhooks/telegram/inbox"
  }
}
```

Return: `0` when both registrations succeed; `1` otherwise.

## `sk-telegram stop`

Removes the webhook from Telegram and unregisters `telegram` from Skiller.

```text
sk-telegram stop
```

Output: one JSON object.

```json
{
  "status": "ok",
  "skiller": {"status": "ok", "webhook": null},
  "telegram": {"status": "ok", "webhook": null}
}
```

Return: `0` when both sides are stopped; `1` otherwise. Running it again has the same result.

## `sk-telegram send`

Sends one text message.

```text
sk-telegram send <chat_id> <text>
```

Arguments:

| Argument | Type | Description |
|---|---|---|
| `chat_id` | integer | Destination Telegram chat |
| `text` | string | Message body |

Output: none.

Return: `0` after Telegram accepts the message; non-zero on invalid input, missing environment, or Telegram/API failure.

## `sk-telegram send --from-env`

Sends one text message using environment values.

```text
SK_TELEGRAM_CHAT_ID='123456789' \
SK_TELEGRAM_REPLY_TEXT='Hello' \
sk-telegram send --from-env
```

Output: none.

Return: `0` after Telegram accepts the message; non-zero on invalid input, missing environment, or Telegram/API failure.

Constraint: positional `chat_id` and `text` cannot be combined with `--from-env`.

## `sk-telegram poll`

Continuously prints received text messages as JSON Lines.

```text
sk-telegram poll [--state-file <path>] [--timeout <seconds>]
```

Options:

| Option | Default | Description |
|---|---:|---|
| `--state-file <path>` | `~/.local/state/monito/telegram/offset` | Stores the next update offset |
| `--timeout <seconds>` | `30` | Positive Telegram long-poll timeout |

Output: one JSON object per text message.

```json
{"update_id": 123, "message": {"chat": {"id": 123456789}, "from": {"username": "user"}, "text": "Hello"}}
```

Return: runs until interrupted; non-zero on invalid input, missing environment, or Telegram/API failure.

## `sk-telegram poll --once`

Waits for one text message, prints it, and exits.

```text
sk-telegram poll --once [--state-file <path>] [--timeout <seconds>]
```

Output: one JSON object followed by a newline.

Return: `0` after printing one text message; non-zero on invalid input, missing environment, or Telegram/API failure. There is no overall inactivity timeout.
