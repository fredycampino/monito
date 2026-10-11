# Use Cloudflared

Use `sk-cloudflared` to guide a human through Cloudflare login and to run a connector only after the human supplies its existing Cloudflared YAML path. Use `uv run sk-cloudflared <command>` when `sk-cloudflared` is not on `PATH`. Do not create another virtual environment.

## Login

A login changes local Cloudflared credentials, so act only after the user explicitly asks to authenticate Cloudflare.

1. Run `sk-cloudflared login status`.
2. If `authenticated` is true, report that no login is needed.
3. If Cloudflared is unavailable, report the diagnostic. Do not install it without approval.
4. Otherwise run `sk-cloudflared login start` and tell the user to complete authorization in the browser opened by Cloudflared.
5. When the user confirms completion, run `sk-cloudflared login status` again.
6. On cancellation, run `sk-cloudflared login stop`; it affects only the login process created by Monito.

Never read or disclose Cloudflared credentials, authorization URLs, or log contents.

## Connector

Cloudflare's remote list does not expose the local YAML or command needed to run a connector. Ask the user for the path to the YAML they already use. Do not read the file; it may contain sensitive settings.

Register the path once, using the tunnel's existing name:

```bash
sk-cloudflared tunnel register --name <tunnel-name> --config <user-provided-yaml-path>
```

Then open, inspect, and close only by that same tunnel name:

```bash
sk-cloudflared tunnel open --name <tunnel-name>
sk-cloudflared tunnel status --name <tunnel-name>
sk-cloudflared tunnel close --name <tunnel-name>
```

`open` starts exactly `cloudflared tunnel --config <registered path> run`. It never reads or modifies the YAML, credentials, DNS, hostname, origin, or remote tunnel. `close` only stops the verified process started by Monito for that name.

Use `sk-cloudflared tunnel list` only to inspect the remote Cloudflare tunnel list. It does not register, configure, or start a connector.
