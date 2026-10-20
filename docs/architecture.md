# Architecture

## Products and layout

One uv workspace contains two distributions:

- `packages/tools`: independent tools and their CLI/HTTP manager.
- `packages/monito`: minimal developer agent, packaged resources and Skiller adapter.
- `packages/tools/src/ggets/health`: bundled health tool and operational template.

Namespace packages have no `__init__.py`. Tests belong to their package or module.
There is no compatibility layer for the deleted standalone integrations.

## Responsibilities

Modules own defaults, validation, operations, commands and OpenAPI routers.
The manager owns configuration loading, explicit registration and lifecycle.
CLI and HTTP call the same service logic. Modules do not import the manager.

Each registry entry declares a factory and an explicit tuple of enabled operations.
A factory receives the module configuration and those operations and returns an object exposing
`register_cli(parser)`, `router`, and `lifespan()` (a synchronous context manager).
The manager enters that context only for the HTTP application lifetime.
CLI commands call their selected service without entering module lifespans.
The single registry explicitly registers health for all environments. There is no
separate development entry point or flavor.

## Configuration

`GGETS_CONFIG_FILE` selects JSON at `~/.monito/ggets/config.json` by default.
A missing default uses defaults; a missing explicit path fails. Unknown sections
fail. Each module receives only its own object. `server` contains host, port and
optional `token_file` for HTTP Bearer authentication.
Operation inputs, results and errors use JSON. CLI help remains human-readable.

The target includes extras `[module]` and `[all]`; none are invented for the bundled
health module. Their relationship to build-time registration remains pending.

## Deployment and security

Docker separates Monito from Tools; consumers use HTTP or local CLI. Tools alone
receives provider credentials. No shared secrets or Docker socket. Modules in the
same Tools process are not isolated from each other. Local CLI under the same
identity as an agent does not isolate credentials. LLM settings remain global.
Public routing is deployment infrastructure, not agent behavior.

## Preserved agent

Root `monito/` stays intact, outside the new packages and images. Renaming it is a
later decision. The new profile defaults to restricted permissions. Runtime and
TUI source are not changed.

## Release and verification

Use one uv lockfile and development environment. Root `VERSION` is authoritative;
package-local copies support isolated builds and must match it. Both distributions
share the release version. Verify unit behavior, CLI/HTTP equivalence, configuration,
authentication, packaged resources and availability of health in installed wheels.
See [module rules](tool-module-rules.md) and [manager rules](tool-manager-rules.md).
