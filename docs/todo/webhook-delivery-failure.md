# Webhook delivery failure

The generic listener forwards an event to its subscriber using `input receive`.
If forwarding fails, the shell step fails and the listener stops. There is no
retry or documented retention policy for the event already received. Do not
assume Telegram retries an event already acknowledged upstream.

Define and verify recovery and event-retention behavior for failed deliveries,
without adding Telegram-specific logic to the generic flow.
