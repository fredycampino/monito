## Using Health

Health checks instance availability and reports system information. It does not check external providers.

Base URL: `http://ggets:8000`.

- `/health/check`: check availability and instance label.
- `/health/info`: get Python version, operating system, and architecture.

Read `GET http://ggets:8000/health/help` for available operations and request examples.
