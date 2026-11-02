# Telegram API

Enabled operations and request examples are exposed by `GET /telegram/help`.
Requests use JSON. Credentials remain in Ggets.

## POST /telegram/typing

```json
{"chat_id": 3, "timeout": 30}
```

- `chat_id`: integer Telegram chat ID.
- `timeout`: integer seconds, 1–120, default 5.

Response after the initial Telegram call, without waiting for the lease to finish:

```json
{"status": "ok", "data": {"chat_id": 3}}
```

Ggets sends `sendChatAction` with `action: typing` immediately. Every four seconds
it independently chooses whether to renew (70% probability) or skip (30%). A skip
may let the native indicator expire and later reappear. The timeout bounds the
renewal lease, not the visibility of Telegram's last action (up to five seconds).

A repeated request for the same chat replaces its deadline with a fresh timeout,
without duplicating the worker. A successful `/telegram/send` for that chat
cancels its lease. Failed sends retain the lease. Renewals and replies for the same chat are
serialized, preventing an older renewal from being sent after a successful reply.
Network calls do not hold the global state lock, so a slow renewal does not block
replies to other chats. The scheduler skips busy chats and retries after 250 ms
without busy-waiting, allowing other chats to renew. Deadlines are rechecked
before each renewal.
Other chats retain their own deadlines. Stopping the integration clears all
leases; application shutdown stops the worker. Leases do not survive restarts.

Errors: `422` invalid input, `503` configuration error, `502` initial Telegram
request failure. Renewal failures are logged without provider details and do not
fail message delivery or subsequent replies.

Typing is HTTP-only: a short-lived CLI process cannot own renewal tasks or share
cancellation state with the HTTP service. Use one Ggets worker process for this
process-local coordination. Messages sent outside this HTTP service cannot cancel
its leases.
