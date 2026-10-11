# Validate Cloudflare login

## Goal

Validate the human-assisted login workflow of `sk-cloudflared` against a real Cloudflare account before implementing tunnel management.

## Procedure

1. Run `uv run sk-cloudflared login status` and record only non-secret result fields.
2. If already authenticated, temporarily move aside the Cloudflared certificate only with explicit user approval, then restore it after validation. Never print or commit its content.
3. Run `uv run sk-cloudflared login start`.
4. Confirm that the command records a Monito-managed login process under `~/.monito/cloudflared/` and directs the human to complete authorization in Cloudflared.
5. Have a human complete authorization in the browser opened by Cloudflared.
6. Run `uv run sk-cloudflared login status` until it returns `authenticated: true`.
7. Verify `uv run sk-cloudflared login stop` is harmless after successful authentication and does not remove the Cloudflare certificate.
8. Restore any temporarily moved credential and remove only Monito's test process state if needed.

## Acceptance criteria

- `login start` begins a single, Monito-managed human login when unauthenticated.
- Completing browser authorization changes `login status` to `authenticated: true`.
- `login status` does not reveal certificate or credential contents.
- `login stop` never revokes authentication or removes Cloudflare credentials.
- No tunnel, DNS route, or connector is created during validation.

## Security

Never print, log, commit, or share Cloudflare certificates, credentials, authorization URLs, or login-log contents.
