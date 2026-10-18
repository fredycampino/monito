## Using Ggets

Ggets exposes tool modules over HTTP at `http://ggets:8000` on the Compose network. Send and receive JSON. Use the shell tool and Python's standard-library HTTP client.

Consult `GET /<module>/help` for enabled operations and request examples. Use `GET /openapi.json` only when detailed schemas are needed. Do not invent operations or parameters. Report connection and HTTP errors; never claim success without a successful response.
