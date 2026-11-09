# Keep the webhook listener running after a delivery failure

## Problem

The generic listener forwards an event to its subscriber using `skiller input
receive`. If that command fails, the `deliver_event` shell step fails and the
listener stops instead of waiting for the next event.

## Required behavior

- Record the failed delivery and its error.
- Return to `wait_message` and keep the listener run active.
- Do not retry the failed delivery.
- Keep the behavior generic; do not add Telegram-specific logic.

## Acceptance criteria

A failed subscriber delivery is observable without terminating the listener run.
The listener accepts and attempts to deliver the next event normally. The failed
event is not retried.

## Resolution

The delivery command uses GNU timeout with a 30-second deadline and a further
5-second forced-kill grace period. The outer shell step retains a 45-second
timeout and uses check: false, preserving exit_code, stdout and stderr while
continuing to wait_message. No retry is performed. Exit code 124 identifies the
normal internal timeout; forced termination can return 137.

Tests cover command failure followed by a successful invocation, payload
integrity, internal timeout (with a shortened test deadline), and flow structure.
They do not run an end-to-end Runtime webhook session.

The outer step timeout, policy/configuration errors and Runtime exceptions remain
fatal; this change handles subscriber command failures and its internal timeout,
not arbitrary Runtime failures.
