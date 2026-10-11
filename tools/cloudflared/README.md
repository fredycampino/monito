# sk-cloudflared

`sk-cloudflared` gives Monito a small, safe interface for Cloudflare Tunnel. It has two separate jobs:

- complete and check the human Cloudflare login;
- start and stop a connector whose Cloudflared YAML was explicitly supplied by the user.

It does not read, print, edit, or copy the YAML. This matters because the file can reference credentials and other sensitive Cloudflared settings. It does not create tunnels, change DNS, or delete remote resources.

Run commands from the repository with `uv run sk-cloudflared ...` when the executable is not available on `PATH`.

## Sign in to Cloudflare

Start by checking whether the current machine already has a Cloudflare login:

```bash
sk-cloudflared login status
```

If it is not authenticated, start the browser-assisted login:

```bash
sk-cloudflared login start
```

Cloudflared handles the browser authorization and keeps its own credentials. Complete the authorization, then check again with `login status`. `login start` is safe to repeat: it does not start a second login when authentication already exists or a Monito-managed login is pending. Cancel only a login process started by Monito with `login stop`.

Monito stores only non-secret process metadata in `~/.monito/cloudflared/` (or under `MONITO_HOME`). Cloudflared owns its credentials in `~/.cloudflared/`; do not copy, print, or remove them through this tool.

## Register the connector configuration

Cloudflare's remote tunnel list tells us a tunnel name and ID, but it cannot tell us the local YAML command that makes a connector work. The user must provide the path to that existing YAML. Monito stores the path without opening the file:

```bash
sk-cloudflared tunnel register \
  --name skiller \
  --config ~/.cloudflared/skiller-webhooks.yml
```

The tunnel name is the only identity used by Monito. Registering the same name and path again is safe. Registering that name with a different path is refused, so changing a connector configuration cannot happen accidentally.

## Start, inspect, and stop the connector

After registration, start the connector by tunnel name:

```bash
sk-cloudflared tunnel open --name skiller
```

This runs the equivalent of `cloudflared tunnel --config <registered path> run` in the background. It does not inspect the YAML, infer the tunnel ID, or alter Cloudflare, DNS, hostnames, origins, or credentials.

Check the process Monito manages:

```bash
sk-cloudflared tunnel status --name skiller
```

Stop it when it is no longer needed:

```bash
sk-cloudflared tunnel close --name skiller
```

`close` only signals the PID created and verified by Monito for that exact name. It cannot stop a connector started outside Monito or a connector registered under another name.

## List remote tunnels

The remote list is independent of local connector registration:

```bash
sk-cloudflared tunnel list
```

It uses Cloudflare's read-only tunnel list and returns its remote data, including names, IDs, and active connections when Cloudflare reports them. A listed tunnel is not automatically registered or started locally.

## JSON and errors

Every command writes one JSON object. A successful result has `status: "ok"`; an operational error has `status: "error"` and exits non-zero. Outputs never include YAML contents, Cloudflare credentials, login URLs, or log contents.
