# Monorepo Architecture

This document defines the agreed and closed rules for developing, testing, versioning, and distributing Skiller tools.

## 1. Repository Model

The project is a monorepo. All tools are developed in this repository while remaining independent products.

```text
monito/
├── tools/
│   ├── telegram/
│   ├── cloudflared/
│   └── _placeholder/
├── packages/
├── monito/
├── docs/
├── VERSION
├── pyproject.toml
└── uv.lock
```

## 2. Tools

Each capability is implemented as an independent CLI tool under `tools/<name>/`.

```text
tools/<name>/
├── agent/
├── src/
├── tests/
├── pyproject.toml
└── README.md
```

Rules:

- The directory uses the capability name: `tools/telegram/`, `tools/email/`.
- The package and CLI use the same name with the `sk-` prefix: `sk-telegram`, `sk-email`.
- Python modules use the equivalent underscore form: `sk_telegram`, `sk_email`.
- Help is available through `sk-<name> --help`.
- Tools do not depend on other tools.
- Each tool declares its own external dependencies.
- Secrets are provided through environment variables and are never stored in the repository.
- `tools/_placeholder/` documents the expected structure for future tools and is not an installable package.

## 3. Manager Agent

Each tool may include a manager agent under `tools/<name>/agent/`.

The manager contains its configuration, instructions, and flows. Its responsibility is to understand and operate its tool's CLI. It must invoke the installed executable by name without depending on paths relative to the monorepo.

Example:

```text
sk-telegram send --from-env
```

## 4. Shared Code

Code reused by multiple tools belongs under `packages/<name>/`.

Rules:

- Code is extracted only when there is a real reuse requirement.
- Shared packages do not contain tool CLIs.
- Each tool explicitly declares the shared packages it uses.
- Tool-specific logic must not be moved into a shared package.

## 5. Tests

Tests remain next to the unit they verify.

- `tools/<name>/tests/`: tests owned by a tool.
- `packages/<name>/tests/`: unit tests owned by a shared package.
- There is no global test directory.
- There are no cross-tool integration tests because tools are independent.
- Tests must verify useful behavior, not only internal details or implementation snapshots.

## 6. Versioning

All tools and packages share one version defined in `VERSION`.

Rules:

- Tools do not have independent versions.
- Every release increments the global version.
- Every package is published again on each release, even when it has not changed.
- Shared packages and tools always belong to the same release train.
- Git tags use the format `v<version>`.

## 7. Publishing and Installation

Development and publishing are coordinated across the monorepo, while installation remains independent per tool.

Publishing order:

1. Publish shared packages.
2. Publish all tools.

Users install only the capabilities they need:

```text
uv tool install sk-telegram==0.1.0
```

There is no umbrella package that installs every tool.

## 8. Workspace and Virtual Environment

The repository uses one `uv` workspace, one `uv.lock` file, and one root `.venv/` virtual environment.

```text
uv sync --all-packages --all-extras
```

Rules:

- Virtual environments are not created inside `tools/` or `packages/`.
- `.venv/` is not tracked by Git.
- All tools are developed and tested from the workspace root.
- Each tool keeps its own `pyproject.toml`.
- The workspace environment is for development; published tools are installed independently.

## 9. Local Configuration

The nearest `.env` file may contain non-secret local configuration. Exported environment variables take priority.

- `SKILLER_BIN` selects a development or production Skiller executable.
- Without `SKILLER_BIN`, tools use `skiller` from `PATH`.
- Secrets must never be stored in `.env`; they come from the system environment, service configuration, CI, or a secret manager.
- `.env` files are ignored by Git; `.env.example` contains only non-secret examples.

## 10. Monito Agent

`monito/` remains at the repository root because it is the agent responsible for developing this repository.

Monito does not belong to any tool and must not be moved under `tools/` or `packages/`. During development, it uses the workspace's single virtual environment.
