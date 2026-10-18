# Generate deployment configuration

## Problem

Monito's runtime configuration contains the installed wheel resource path
(`/usr/local/lib/python3.12/site-packages/packages`) and the webhook listener's
internal IP. Users must currently copy these values manually. The resource path
depends on Python installation details, and the IP duplicates
`MONITO_INTERNAL_IP` from Compose, risking configuration drift.

## Proposed solution

Provide a deployment setup script that copies the `data-examples/` layout and
completes configuration using deployment settings and the selected image's
installed resource location. Preserve existing user configuration, credentials
and state. Keep the runtime JSON at the configured host path, mounted read-only
at `/etc/monito/config.json`. No build-time or entrypoint generation.

The agent profile is already external, mounted read-only at
`/etc/monito/agent.json`; it is not part of the wheel and must not be overwritten.

## Acceptance criteria

- Users do not need to discover the wheel path or duplicate the internal IP.
- `@monito` and `@webhook` resolve from the installed resources.
- Ggets can reach the configured Skiller webhook server.
- Existing configuration, secrets and persistent data are preserved.
- Setup is repeatable without changing CI, release or the container entrypoint.
