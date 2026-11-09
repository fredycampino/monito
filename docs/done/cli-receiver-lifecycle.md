# CLI operations do not start module listeners

## Status: done

Ggets CLI operations call their selected service directly, without entering
`manager.lifespan()`. Health checks and Telegram sends no longer start the
Telegram receiver or attempt to bind its port.

The FastAPI application used by `ggets serve` retains the global module lifecycle:
listeners start when the application starts and stop when it shuts down.

Regression tests in `packages/tools/tests/test_manager.py` verify:
- `health check` succeeds without entering any module lifecycle.
- `telegram send` invokes its service without entering any module lifecycle;
  the service is mocked, so no Telegram request is made.
- The HTTP application enters all registered module lifecycles and closes them
  in reverse order on shutdown.

Architecture and module/manager contracts are updated accordingly. No live
containers, external services, credentials or user sessions were changed.
