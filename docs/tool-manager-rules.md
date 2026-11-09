# Tool Manager Rules

## Definition

The **tool manager** registers modules, injects configuration, and controls their lifecycle. It exposes their operations through CLI and HTTP. Code identifier: `tool_manager`.

The manager directs execution; modules do not need to know it.

## Rules

### 1. Central registry

The registry determines which modules and operations are exposed through CLI and HTTP at build time, not through dynamic runtime discovery.

Each registry entry declares a factory and a tuple of enabled operations.
Each registered factory receives the module configuration object and that tuple, returning an instance with `register_cli(parser)`, `router`, and `lifespan()`. The latter is a synchronous context manager that the manager enters and exits
for the HTTP application lifetime, not for individual CLI operations.

### 2. Exposure, not business logic

The manager registers and exposes module-provided commands and OpenAPI contracts. It neither implements nor duplicates their business logic.

- CLI: `ggets <tool-module> ...`
- HTTP: `/<tool-module>/...`

Operation inputs, outputs, and errors use JSON in both interfaces. CLI help retains its standard human-readable format.

### 3. Single global configuration

The manager loads one JSON file. An environment variable provides its path; otherwise, it uses `~/.monito/ggets/config.json`.

The variable is `GGETS_CONFIG_FILE`. A missing default file uses defaults; a missing explicitly configured path produces an error.

The global object contains an optional `server` section and one section per
registered module. Unknown top-level sections and non-object module sections
are rejected. For example:

```json
{
  "module0": {},
  "module1": {},
  "module3": {
    "a": {},
    "b": 1
  }
}
```

The manager injects only the following into `module3`:

```json
{
  "a": {},
  "b": 1
}
```

It does not interpret internal fields. Each module provides defaults and validates its section. Minimize environment variables for individual fields.

### 4. Server configuration

Server configuration belongs to the manager, not tool modules. It includes an optional token for HTTP authentication.

The `server` section accepts `host`, `port`, and `token_file`. The token is read from the file and checked using Bearer authentication. The application default listener is `127.0.0.1:8000`, without a token.
Compose overrides the address through the mounted JSON to bind the API to the
internal interface. Compose variables do not update JSON automatically.

This authentication protects the manager API, not module-owned provider
listeners. Telegram owns a separate ingress server and validates Telegram's
webhook secret there; it is not an unauthenticated route on the tools API.

### 5. Lifecycle

The manager controls initialization, execution, and cleanup of modules and their resources. Modules provide the required interfaces without depending on the manager.

### 6. Distribution

The distribution is `ggets`, built from `packages/tools`. It includes the
manager and the Health and Telegram modules declared in `ggets.registry.MODULES`.
No installation extras or runtime plugin discovery are currently defined.
Modules are not published as separate packages.

The Ggets wheel is installed in its container image. Current CI validates Python
distributions but does not publish them to PyPI. See [Workflows](workflows.md)
for the shared Monito/Ggets release and image publication policy.

### 7. Installation without external side effects

Installation does not start services, register webhooks, or modify providers. Such actions require explicit subsequent operations.

### 8. Manager-owned unit tests

The manager maintains unit tests for configuration, registration, transport, and lifecycle. Tests use doubles without importing or executing concrete modules.

Manager–module and real-provider E2E coverage remains to be defined; manager
unit tests are not proof of end-to-end delivery.

## Scope

These rules define manager responsibilities; implementation details above reflect
the current registry and packaging. Module internals are defined in
[tool-module-rules.md](tool-module-rules.md). Deployment addresses, mounts and
network isolation are defined in [docker-spec.md](docker-spec.md).
