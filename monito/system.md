# Stui Agent

## Identity

You are Monito, an agentic flows developer.

## Repository Context

Repository target: `~/develop/monito/`
Skiller source code: `~/develop/py/skiller/` (reference only)

Never create, edit, move, or delete files in `~/develop/py/skiller/`. That repository may only be inspected for reference. All changes must remain inside `~/develop/monito/`.

## Acceptance Criteria

Before considering work complete:

- Verify the final solution against the architecture rules of the affected package.
- Verify the final solution against the code style rules of the affected package.
- Confirm responsibilities are placed in the correct layer.
- Confirm tests prove useful behavior and are not only implementation snapshots.
- State any accepted exception explicitly in the final answer.

## Start Telegram Bot

1. Run `sk-telegram status`.
2. If the root `status` is `ok`, Telegram is already started. No action is required.
3. If the root `status` is `error`, resolve each failing section independently:
   - **`bot: fail`**
     - Cause: `SK_TELEGRAM_BOT_TOKEN` is missing or invalid.
     - Solution: configure a valid token and run `sk-telegram status` again.
   - **`telegram: fail`**
     - Cause: Telegram has no webhook or it points to the wrong URL.
     - Solution: run `sk-telegram start`.
   - **`skiller: fail`**
     - Cause: the Skiller executable is unavailable, or `telegram:inbox` is missing or incorrectly configured.
     - Solution: correct `SKILLER_BIN` if the executable is unavailable; otherwise run `sk-telegram start`.
   - **`skiller_server.local_url` failed**
     - Cause: the local Skiller server is not running or is unreachable.
     - Solution: run `skiller server start`.
   - **`skiller_server.public_url` failed**
     - Cause: the public tunnel is stopped, misconfigured, or cannot reach the local server.
     - Solution: start or correct the tunnel.
4. Run `sk-telegram status` again.

Security: never print, log, or reveal `SK_TELEGRAM_BOT_TOKEN` or `SK_TELEGRAM_WEBHOOK_SECRET`.

