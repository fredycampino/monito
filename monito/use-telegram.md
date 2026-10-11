# Use Telegram

## Start Telegram Bot

Security: never print, log, or reveal `SK_TELEGRAM_BOT_TOKEN` or `SK_TELEGRAM_WEBHOOK_SECRET`.

When `sk-telegram` is unavailable on `PATH` in this repository, run it through the workspace environment instead: `uv run sk-telegram <command>`. Do not create or use a tool-local virtual environment.

1. Run `sk-telegram status` (or `uv run sk-telegram status` when the executable is not on `PATH`).
2. If the root `status` is `ok`, Telegram is already running. No action is required.
3. If the root `status` is `error`, resolve each failing section independently:
   - **`bot: fail`**
     - Cause: `SK_TELEGRAM_BOT_TOKEN` is missing or invalid.
     - Action: ask the user to configure a valid token. Never request or display its value.
   - **`telegram: fail`**
     - Cause: Telegram has no webhook or it points to the wrong endpoint.
     - Action: run `sk-telegram start`.
   - **`skiller: fail`**
     - Cause: the Skiller executable is unavailable, `telegram:inbox` is incorrectly configured, or no run is waiting for it.
     - Action:
       - Correct `SKILLER_BIN` if Skiller is unavailable.
       - Run `sk-telegram start` if the webhook is missing or invalid.
       - Start the Telegram flow if no run is waiting for `telegram:inbox`.
   - **`skiller_server.local_url` failed**
     - Cause: the local Skiller server is stopped or unreachable.
     - Action: ask the user for explicit approval before running `skiller server start`.
   - **`skiller_server.public_url` failed**
     - Cause: there is no public Internet route to the local Skiller server, or the tunnel is stopped or misconfigured.
     - Action: ask the user to start or fix the public tunnel or network route. Do not configure or start it without approval.
4. Run `sk-telegram status` again.
5. Present a short, user-friendly summary:
   - Bot identity.
   - Telegram webhook.
   - Waiting run.
   - Local server.
   - Public access.
   - Overall result.

## Stop Telegram Bot

1. Run `sk-telegram status` and report the current state.
2. Run `sk-telegram stop`.
3. Do not delete the Telegram run. It must remain available to preserve its history and memory.
4. Do not stop the Skiller server. Other applications may depend on it.
5. If the user also wants to stop the Skiller server, explain the possible impact and request explicit confirmation before running `skiller server stop`.
6. Leave the public tunnel running and inform the user that it remains open.
7. Run `sk-telegram status` again.
8. Present a short, user-friendly summary:
   - Telegram webhook stopped.
   - Run preserved.
   - Skiller server still running.
   - Public tunnel still open.
