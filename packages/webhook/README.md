# Webhook listener

Forwards every webhook payload as text input to a subscriber, prefixed with
`labels`. No filtering, content validation or external script; empty payloads
are forwarded too.

```bash
skiller run ./packages/webhook/webhook.yaml \
  --arg run_id=<subscriber-run-id> \
  --arg webhook=telegram \
  --arg key=inbox \
  --arg 'labels=[Notification][Telegram]'
```

Use the same Skiller environment/database as the subscriber. Requires a running
Skiller server. The first step registers the named webhook with POST, JSON and
`auth=none`; `ALREADY_REGISTERED` also continues to the wait. Other registration
errors fail the flow. Existing registration settings are not overwritten. The correlation key is
provided through `key`: the receiver URL is `/webhooks/<webhook>/<key>`.

For GgTelegram, registration currently requires POST, JSON and `auth=none`,
because delivery sends no authentication. Do not expose this unauthenticated
receiver publicly.

Delivery errors fail the listener; no retry or durable delivery guarantee.
Duplicate listeners are rejected by Skiller when starting a run with the same
webhook/key already being waited on. The caller receives Skiller's original JSON
error `WEBHOOK_WAIT_CONFLICT`, including the existing run ID, and exit code 1.
Registration is not used as a lock and the flow adds no replacement conflict message. Keep that
CLI output visible to the calling agent.
