# Use Telegram

## Start Skiller Server

Run `skiller server start` to start the local server and `skiller server status`
to check its state. In Box, run these commands inside the container.

Telegram requires a public HTTPS endpoint, for example
`https://<your-domain>/webhooks/telegram/inbox`.
Publishing that endpoint is deployment infrastructure, not Monito's responsibility.

## Start Telegram Receiver

Run `skiller run @telegram` to start the receiving flow. It waits for messages
on `telegram:inbox` and processes them when they arrive.

## Start Telegram Bot

Run `sk-telegram start` to register `telegram:inbox`, save its authentication
secret in Skiller, and configure the Telegram webhook. The command takes no
arguments and uses the configured credentials and public endpoint.

It does not launch the receiving flow.

The response is one JSON object:

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

Exit code `0` means both configurations succeeded; `1` means failure. Configuration
failures return `status: "error"` and details in the corresponding section;
missing required settings can terminate with a message instead of JSON.

## Status Telegram Bot

Run `sk-telegram status` without arguments to check the bot identity, the Telegram
webhook, the Skiller registration and waiting run, and local and public server
access. It reports the current state without changing configuration.

The response is one JSON object:

```json
{
  "status": "ok",
  "bot": {"status": "ok", "id": 123456789, "username": "example_bot"},
  "telegram": {
    "status": "ok",
    "webhook": "https://skiller.example/webhooks/telegram/inbox"
  },
  "skiller": {
    "status": "ok",
    "version": "0.1.0-beta.43",
    "path": "/usr/local/bin/skiller",
    "webhook": "telegram:inbox",
    "run_id": "example-run-id"
  },
  "skiller_server": {
    "status": "ok",
    "local_url": "http://127.0.0.1:8001/health",
    "public_url": "https://skiller.example/health"
  }
}
```

Exit code `0` and root `status: "ok"` mean every section passed. Otherwise,
the exit code is `1`, the root status is `error`, and failing sections report
`status: "fail"`. Missing values appear as `null`; URL failures include error
details. A configured Telegram webhook alone does not mean the bot is ready:
Skiller also needs a run waiting for `telegram:inbox` and reachable server endpoints.

### Example: server access failure

```json
{
  "skiller_server": {
    "status": "fail",
    "local_url": "http://127.0.0.1:8001/health: Connection refused",
    "public_url": "https://skiller.campino.me/health: HTTP 530"
  }
}
```

- `Connection refused`: the local server is not started.
- HTTP `530`: the public tunnel/domain is not working.

## Stop Telegram Bot

Run `sk-telegram stop` without arguments to remove the webhook from Telegram and
unregister it in Skiller. It does not delete runs or stop the server or tunnel.

Example: `sk-telegram stop`.

The response is a JSON object with `status`, `skiller`, and `telegram`.
Exit code `0` means both removals succeeded; `1` means failure.

## Send Message

Run `sk-telegram send <chat_id> "<text>"` to send a text message to a chat.
For example: `sk-telegram send 123456789 "Hello"`.

It produces no output on success and exits with code `0`. Errors produce a
non-zero exit code. Sending does not require an incoming webhook.

## Poll Messages

Run `sk-telegram poll --once` to wait for one text message and print it as JSON.
Without `--once`, it continues receiving messages. `--timeout <seconds>` sets
the long-poll timeout; `--state-file <path>` selects the file holding the offset.

Polling is an alternative to webhooks: Telegram does not allow polling while a
webhook is configured.

```json
{
  "update_id": 123,
  "message": {
    "chat": {"id": 123456789},
    "from": {"username": "example_user"},
    "text": "Hello"
  }
}
```
