# Telegram typing indicator

## Problem

After sending a message to Monito through Telegram, the user receives no feedback
until a reply arrives. It is unclear whether the message was received or the
agent is working, resulting in poor conversational UX.

## Desired behavior

Show Telegram's typing indicator when an incoming message is accepted for
processing, and refresh it while Monito works until its reply is sent.
Use Telegram Bot API `sendChatAction` with `action: typing`; the indicator lasts
up to five seconds and needs periodic renewal for longer processing.

## Investigation

- Check whether Ggets already exposes `sendChatAction`; do not assume it does.
- Identify the appropriate processing lifecycle hooks across the webhook listener,
  Monito and Ggets. Merely receiving a webhook does not prove the agent is working.
- Keep renewal automatic rather than depending on repeated agent tool calls.
- Define cleanup on successful reply, failure, interruption and processing timeout.
- Handle concurrent messages and chats without duplicate renewal loops or stopping
  another active operation's indicator.
- Keep credentials in Ggets; do not expose them to Monito or the listener.

## Acceptance criteria

- An accepted Telegram request shows typing promptly during agent processing.
- The indicator is renewed during longer processing and stops on reply or termination.
- Failures to send chat actions do not block message delivery or fail subscriber
  and listener runs; no typing loop is left running indefinitely.
- No extra chat messages are sent just to acknowledge processing.
- Tests use mocked Telegram calls and isolated state; a live Telegram test requires
  explicit authorization.

Implementation approach and ownership are pending investigation. This indicator
improves feedback but does not fix failed reply delivery or the separate Skiller
shell-policy false positive.
