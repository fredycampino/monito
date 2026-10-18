# Webhook subscriber handover

## Problem

The webhook listener and its subscriber are separate runs. The listener stores the destination `run_id` in its inputs and waits on a `webhook + key` pair.

If the subscriber terminates or stops accepting input, the listener can remain waiting with the old destination. Starting another listener for the same webhook and key is rejected with `WEBHOOK_WAIT_CONFLICT`, even though the destination may no longer be usable.

On the next event, the existing listener attempts `input receive` against the old run. If delivery fails, the shell step fails; there is currently no recovery, subscriber replacement or explicit handling of the undelivered event.

Closing the STUI is not sufficient evidence that a subscriber is dead: its run may still accept input. An existing webhook registration is also distinct from an active listener.

## Required behavior to define

- Distinguish a disconnected UI, a temporarily unavailable subscriber and a terminal or missing run, using verified Skiller states and input behavior.
- Provide explicit, authorized handover to a new subscriber without silently replacing a valid one.
- Report the existing listener and destination when a subscription cannot be established.
- Define what happens to an event already received when forwarding fails: retry, retain or report it as undelivered. Do not assume Telegram will retry an event already acknowledged upstream.
- Preserve the generic listener contract; avoid Telegram-specific logic.

## Possible approaches

- A controlled replacement procedure: inspect the existing listener and subscriber, obtain approval, stop or delete the old listener as supported by Skiller, and start a new one. Deletion removes run data and must not be automatic.
- A mutable subscription mapping resolved at delivery time, with an explicit operation to change the destination. This adds persistence and coordination beyond the current minimal flow.

These are proposals, not implemented behavior. Verify lifecycle, conflict and ingress semantics before choosing an approach.

## Acceptance criteria

- A terminated subscriber cannot leave the integration indefinitely blocked without actionable feedback.
- A valid subscriber is never replaced implicitly.
- Handover does not create competing listeners for the same webhook and key.
- Delivery failures have a documented recovery and event-retention policy.
- Tests cover subscriber termination, UI disconnection, conflicting listeners and authorized replacement.
