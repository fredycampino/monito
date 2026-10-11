# Cloudflared manager

Use `sk-cloudflared` only through its documented commands. If the executable is not on `PATH`, run it as `uv run sk-cloudflared <command>` from the Monito workspace. Do not create a tool-local virtual environment.

For Cloudflare authentication, first run `login status`. Start `login start` only when the user explicitly requests authentication and it is not already authenticated. Ask the user to complete the browser authorization and verify with `login status`. Never read or disclose credentials, authorization URLs, or logs.

For a connector that already works outside Monito, ask the user for its tunnel name and the exact YAML path used to run it. Register it with `tunnel register --name <tunnel-name> --config <user-provided-yaml-path>`. The YAML may be sensitive: do not read, print, edit, copy, or validate its contents. The tunnel name is the only identity used by Monito.

Use `tunnel open`, `tunnel status`, and `tunnel close` only with that registered tunnel name. `open` starts Cloudflared with the stored YAML path; it must not change remote tunnels, DNS, hostnames, origins, or credentials. `close` only affects the process created and verified by Monito for that exact name.

Use `tunnel list` only as a read-only view of remote Cloudflare tunnels. A remote list entry is not a local connector configuration and must not be started or registered automatically.
