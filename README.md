# Monito and Tools

Two distributions: `packages/monito` and `packages/tools`.
The original `monito/` is preserved, but excluded from new images and packages.

## Development

```bash
uv sync --all-packages
uv run pytest
uv run ruff check .
uv run ggets health check --json '{}'
uv run ggets health info --json '{}'
uv run ggets serve
uv build --all-packages
```

The bundled `health` module exposes `POST /health/check` and `POST /health/info`
with JSON `{}`. `info` reports Python version, operating system and architecture;
it does not expose paths or environment variables.
OpenAPI: `/openapi.json`; Swagger UI: `/docs`.
The same module and registry are used locally and in production, including Docker.
No placeholder extras or compatibility commands are provided.

## Configuration

`GGETS_CONFIG_FILE` selects one JSON file, defaulting to
`~/.monito/ggets/config.json`. A missing default uses defaults; an explicit
missing path fails. Example:

```json
{
  "server": {"host": "127.0.0.1", "port": 8000},
  "health": {"label": "local"}
}
```

Optional `server.token_file` enables Bearer authentication, including docs.
Do not store tokens in configuration or source control.

## Docker

`docker compose build` creates `monito-box:dev` and `ggets:dev` using the
Dockerfiles in `docker/`. Start Ggets with `docker compose up -d ggets`.
Its internal URL is `http://ggets:8000`; no host ports are published.

For Monito, prepare writable `data/monito/home` and `data/monito/workspace` owned by its
container user (UID/GID 10001 by default, overridden by `HOST_UID`/`HOST_GID`).
`docker compose run --rm monito` opens the current interactive agent.
LLM settings belong in its persistent home, not in the image.

See [Docker specification](docs/docker-spec.md) for layout, security and the
production target. Service-mode Monito and its Ggets client remain pending.

See [architecture](docs/architecture.md), [module rules](docs/tool-module-rules.md)
and [manager rules](docs/tool-manager-rules.md).

## Release and deployment

See [workflows](docs/workflows.md) for Feature → Release → Publish → Deploy,
and [versioned deployment](docs/deployment.md) for deploying and rolling back the
published Monito/Ggets image pair. Python distributions are currently validated
in CI, not published to PyPI.
