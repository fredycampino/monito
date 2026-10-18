# CLI starts the Telegram receiver lifecycle

## Problem

A Ggets CLI operation enters all registered module lifecycles, including the
Telegram receiver lifecycle. When Telegram is configured, a command may therefore
attempt to bind the receiver address and port even though the operation does not
need to receive webhooks.

If `ggets serve` already owns that address and port, the CLI can fail with an
address-in-use error before executing the requested operation. This affects
commands for other modules too, because lifecycle entry is manager-wide.

## Diagnosis

- `packages/tools/src/ggets/cli.py`: non-server commands execute inside
  `with manager.lifespan()`.
- `packages/tools/src/ggets/tool_manager.py`: the manager enters every registered
  module's lifecycle, not just the selected command's module.
- `packages/tools/src/ggets/telegram/module.py`: Telegram's lifecycle delegates to
  `receiver_lifespan(service)`.
- `packages/tools/src/ggets/telegram/receiver.py`: when the required configuration
  fields are present, lifecycle entry reads the webhook secret, binds a socket,
  and starts the receiver thread before yielding. Exit stops the receiver.

This is a lifecycle and availability issue identified from the code, not a
verified security exploit. An unnecessary listener adds temporary network
surface, but retains webhook-secret validation. A bind conflict does not by
itself displace an existing listener, bypass authentication, or demonstrate
container escape. No concurrent CLI/service reproduction was performed for
this diagnosis.
