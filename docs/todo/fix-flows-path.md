# Stable path for packaged flows

## Problem

Monito currently configures `flow_paths` with `/usr/local/lib/python3.12/site-packages/packages`. This is the mirror of the repository resources installed by the wheel, but it exposes a Python installation detail to deployment configuration. Users should not need to discover that path, and it may change with the Python version or installation environment.

Keep the current wheel layout and configured path until this task is implemented.

## Proposed solution

- During the Docker build, install the wheel and copy its packaged resources to `/opt/monito/packages`, preserving the `monito/` and `webhook/` directory structure.
- Set the example runtime configuration to `{"flow_paths": ["/opt/monito/packages"]}`. Users can add their own flow directories without knowing the Python installation path.
- Update the `agent.json` bind mount and the Monito launcher to use the same resource tree, avoiding two active copies with different configuration.
- Keep resources owned by root, directories at `755` and files at `644`. The container filesystem and the agent profile mount remain read-only.
- Update deployment documentation and tests.

This moves only flow resources (YAML, prompts and instructions), not the `skiller` executable. The wheel remains the source of the installed resources.

## Alternative: generated packaged flow path

- Discover the wheel resources directory automatically during installation or startup, instead of requiring users to configure the Python installation path.
- Generate the packaged flow path separately from user configuration; never overwrite the user's `config.json`.
- Combine that discovered path with user-defined `flow_paths`. An empty user list should still allow `@monito` and `@webhook` to resolve.
- Keep resources in the wheel installation directory, avoiding a copy under `/opt`.

The mechanism for combining generated and user configuration must be verified against Skiller's configuration contract before implementation. This is an alternative proposal, not existing behavior.

## Deployment-derived webhook listener configuration

The runtime JSON also needs `webhooks.host` to match Monito's internal IP
(`MONITO_INTERNAL_IP` in Compose). The default `127.0.0.1` prevents Ggets from
reaching Skiller. Maintaining this IP in both files risks configuration drift.
A generated configuration could derive the listener address from deployment
settings together with the discovered packaged flow path, without overwriting
user configuration. Network access and precedence rules must be tested.

## Acceptance criteria for the fixed-path proposal

- The deployment configuration no longer references `site-packages` or a Python version.
- `@monito` and `@webhook` resolve from `/opt/monito/packages`.
- The launcher uses the same Monito resources and mounted profile.
- Monito can read the resources but cannot modify them.
- Building and recreating the container preserves user configuration and persistent data.
