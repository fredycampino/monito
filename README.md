# Monito

Monito is an AI agent running in Box, a container with a persistent workspace and
home. Ggets provides its tools and integrations. Nexo is the independent host
agent used to develop and maintain this repository.

## Components

### Monito: the Box agent

`packages/monito` contains Monito's flow, system prompt and instructions.
Box includes Skiller, Chromium and browser tools. Agent state and credentials
remain in the persistent home, outside the image; work belongs in the workspace.
The agent profile and Runtime configuration are mounted read-only.

### Ggets: services and tools

`packages/tools` provides the `ggets` CLI and FastAPI server. Registered modules
expose the same services through both interfaces. Current modules are Health and
Telegram. CLI operations do not start HTTP listeners; `ggets serve` manages their
server lifecycle.

### Nexo: the development agent

`nexo/` contains the host development agent, independent of Monito Box. From the
repository root, start it with `skiller ./nexo/nexo.yaml` using a host Skiller
installation. See [Nexo](nexo/README.md) for its profile and global settings.

## Repository structure

- `packages/monito/`: Monito agent resources and Python distribution.
- `packages/tools/`: Ggets services, CLI, HTTP API and tests.
- `packages/webhook/`: listener flow that delivers incoming events to a subscriber run.
- `nexo/`: host development flow, profile and instructions.
- `docker/` and `compose.yaml`: container builds and deployment configuration.
- `data-examples/`: configuration and persistent-data layout examples, not live data.
- `docs/`: architecture, development rules and operating procedures.

## Local development

### Installation

Use Python 3.12 and uv. From the repository root:

```bash
uv sync --all-packages
```

Ggets can run directly on the host:

```bash
uv run ggets health check --json '{}'
uv run ggets health info --json '{}'
uv run ggets serve
```

### Tests and validation

```bash
uv run pytest
uv run ruff check .
uv build --all-packages
```

See [workflows](docs/workflows.md) and [CI](.github/workflows/ci.yml) for the
additional branch, changelog, configuration and container checks required for PRs.

## Configuration

For Ggets, `GGETS_CONFIG_FILE` selects one JSON file, defaulting to
`~/.monito/ggets/config.json`. A missing default uses defaults; an explicit
missing path fails. A minimal host configuration is:

```json
{
  "server": {"host": "127.0.0.1", "port": 8000},
  "health": {"label": "local"}
}
```

Optional `server.token_file` enables Bearer authentication, including API docs.
Store credentials outside source control and images, not as tokens in configuration.

Box uses a separate agent profile at `/etc/monito/agent.json` and Runtime
configuration at `/etc/monito/config.json`. Its persistent HOME is `/data/home`
and workspace is `/data/workspace`. Provider settings and secrets belong in the
persistent home. Nexo configuration is not used by Box.

Use [data examples](data-examples/) and the [local deployment guide](docs/local-deployment.md)
for required files, host paths, permissions and network settings. Configuration
generation is not implemented; preserve existing settings, credentials and state.

## Running with Docker

### Local deployment

Docker Engine and Docker Compose are required; the network configuration requires
Compose 2.33.1 or later. First complete the preparation steps in
[local deployment](docs/local-deployment.md), including environment files, required
configuration files and writable data directories owned by the configured UID/GID.
From the repository root, select the Compose environment file once for the current
shell, then build and start the local images:

```bash
export COMPOSE_ENV_FILES=docker/compose.env
docker compose build
docker compose up -d
docker compose ps
```

The following Docker commands assume that variable remains set in the current shell.

Local builds use `monito-box:dev` and `ggets:dev`. Published deployments use an
explicit version for both images; see [versioned deployment](docs/deployment.md).
Do not build or recreate an existing deployment without reviewing its configuration
and preserving its data and sessions.

### Optional Android control

The optional `mobile` service combines ADB, Appium and UiAutomator2 for Android
control. Enable it explicitly with `docker/compose.mobile.yaml`; the base
Compose deployment does not start it. Only Monito can reach its private network,
and neither ADB nor Appium ports are published.

See [Android mobile setup](docs/android-mobile.md) for USB permissions, persistent
ADB keys, configuration and deployment precautions.

### Open a Monito session

In the running Box container:

```bash
docker compose exec monito skiller @monito
```

For a shell, use `docker compose exec monito sh`.
Opening `@monito` creates a new run; it does not resume an existing session.

### Service health and status

```bash
docker compose logs --tail=50
docker compose exec ggets ggets health check
docker compose exec monito skiller server status
```

The CLI Health check returns a fixed `status: "ok"` and the configured label;
it does not probe the HTTP server, Telegram or Skiller. The Health HTTP endpoints
are `POST /health/check` and `POST /health/info`, both accepting JSON `{}`.
`info` reports Python version, operating system and architecture, not paths or
environment variables. OpenAPI is at `/openapi.json` and Swagger UI at `/docs`.

Inside the Compose network, the tools API is `http://ggets:8000` and is not
published to the host. Only the Telegram receiver is published, by default at
`127.0.0.1:8001`. The Box entrypoint starts the Skiller HTTP server, but does not
create or resume subscriber runs or webhook listeners. See the local deployment
guide for independent HTTP reachability checks.

## Telegram integration

Incoming messages follow this route:

```text
Telegram → public HTTPS tunnel → Ggets receiver → Skiller webhook server
         → @webhook listener → Monito subscriber run
```

For incoming Telegram tasks, the flow activates a typing indicator and sends
Monito's final answer automatically through Ggets to the original chat. The agent
must not send that reply manually. Local input is not forwarded to Telegram.

Setup requires Telegram credentials, a public HTTPS URL, reachable private
services and a waiting subscriber/listener in the same Skiller database. Do not
enable the integration merely as a health check.

Follow [Monito's Telegram instructions](packages/monito/instructions/use-telegram.md)
and the networking instructions in [local deployment](docs/local-deployment.md).
A `WAITING` run does not prove that the HTTP server or actual message delivery works.

## Release and deployment

The delivery sequence is **Feature → Release → Publish → Deploy**.
Feature PRs target `main`, contain exactly one commit on the current `origin/main`
and add a meaningful `Unreleased` changelog entry. Release and deployment require
separate approval; publishing images does not update a running environment.

The two base images use the same explicit published version:
- `ghcr.io/fredycampino/monito-box:<version>`
- `ghcr.io/fredycampino/ggets:<version>`

Android-enabled deployments also require
`ghcr.io/fredycampino/monito-mobile:<version>` from the same release. Confirm all
required images are published and pull them before recreating any service.

See [workflows](docs/workflows.md) for release and publication, and
[versioned deployment](docs/deployment.md) for upgrades and rollback. Python
wheels and source distributions are validated in CI, not published to PyPI.

## Reference documentation

- [Architecture](docs/architecture.md)
- [Tool module rules](docs/tool-module-rules.md) and [manager rules](docs/tool-manager-rules.md)
- [Docker specification](docs/docker-spec.md)
- [Local deployment](docs/local-deployment.md)
- [Android mobile setup](docs/android-mobile.md)
- [Versioned deployment](docs/deployment.md)
- [Development and delivery workflows](docs/workflows.md)
- [Changelog](CHANGELOG.md)
- [Nexo development agent](nexo/README.md)
- [Monito Telegram instructions](packages/monito/instructions/use-telegram.md)
