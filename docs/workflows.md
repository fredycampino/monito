# Workflows

Monito separates product delivery into four workflows:

```text
feature -> release -> publish -> deploy
```

A workflow must finish before its output is used by the next one. Publishing an artifact does not deploy it; deployment always selects an explicit published version.

## Responsibilities

- `[dev]`: implements and validates product changes.
- `[admin]`: owns approvals, release decisions, credentials, registries, and deployed environments.
- `[ci]`: executes repeatable checks and publishes only after the required trigger or approval.

## Feature

**Purpose:** develop an isolated product change.

**Input:** `main`.

**Output:** reviewed change merged into `main`.

1. `[dev]` creates `feature/<topic>` from `main`.
2. `[dev]` implements the change, useful tests, and relevant documentation.
3. `[dev]` adds at least one user-relevant entry under the top-level `Unreleased` section in `CHANGELOG.md`.
4. `[dev]` runs focused local verification.
5. `[dev]` squashes the feature branch so the pull request contains exactly one commit.
6. `[dev]` opens a pull request to `main`.
7. `[ci]` rejects pull requests with more than one commit or without an `Unreleased` changelog entry; otherwise it runs linting, tests, flow validation, and container build checks.
8. `[admin]` reviews and approves the change.
9. `[admin]` merges the approved pull request into `main`.

`main` must remain releasable. Feature work does not change a deployed environment.

## Release

**Purpose:** choose and freeze a version from `main`.

**Input:** a releasable commit on `main`.

**Output:** an annotated Git tag `vX.Y.Z`.

1. `[admin]` selects the next semantic version.
2. `[dev]` creates `release/X.Y.Z` from `main`, moves the accumulated `Unreleased` entries to a dated `X.Y.Z` section in `CHANGELOG.md`, creates a new empty `Unreleased` section, and updates `VERSION`.
3. `[dev]` squashes the release branch so the pull request contains exactly one commit.
4. `[dev]` opens a pull request to `main`.
5. `[ci]` rejects release pull requests with more than one commit; otherwise it verifies version consistency, changelog structure, tests, flows, and the container build.
6. `[admin]` reviews and merges the release preparation into `main`.
7. `[admin]` creates or authorizes the annotated tag `vX.Y.Z` on that merge commit.

The tag identifies the exact source used for publication. No deployment occurs in this workflow.

## Publish

**Purpose:** build and distribute artifacts for an existing release tag.

**Input:** Git tag `vX.Y.Z`.

**Output:** immutable artifacts available from registries.

1. `[ci]` checks out the tag and repeats release verification.
2. `[ci]` builds and publishes the OCI image:
   ```text
   ghcr.io/fredycampino/monito-box:X.Y.Z
   ```
3. `[ci]` may also update the mutable convenience tag:
   ```text
   ghcr.io/fredycampino/monito-box:latest
   ```
4. `[ci]` may publish `sk-telegram` and `sk-cloudflared` to PyPI when those standalone CLIs are part of the release policy.
5. `[ci]` records artifact digests and publication results in the release metadata.

Production deployment must use `:X.Y.Z` or, preferably, an OCI digest. It must not rely on `:latest`.

## Deploy

**Purpose:** run a selected, already published version in an environment.

**Input:** an image tag or digest, environment configuration, and persistent data.

**Output:** the selected version running and verified in that environment.

1. `[admin]` selects an explicit release artifact, for example `ghcr.io/fredycampino/monito-box:0.1.0`.
2. `[admin]` updates the environment Compose configuration without changing persistent `data/` or secrets.
3. `[admin]` pulls the image and recreates the service.
4. `[admin]` verifies container status, STUI access, `@monito`, persistent state, and enabled integrations.
5. `[ci]` may run post-deploy checks when a controlled deployment runner is available.

To roll back, `[admin]` redeploys a previously published tag or digest. Persistent data remains in place unless a version-specific migration procedure says otherwise.

## Boundaries

- A feature or release pull request contains exactly one commit. `[ci]` rejects multi-commit pull requests.
- Feature pull requests add at least one entry to the top-level `Unreleased` changelog section; release pull requests turn those entries into the versioned release section.
- `[dev]` does not publish artifacts or deploy production environments.
- `[ci]` receives only the credentials needed for its assigned action.
- `[admin]` owns production secrets and deployment access.
- A release tag is immutable; a correction requires a new version.
- Docker images contain application code and fixed dependencies. User state, credentials, and databases remain outside the image in the deployment's persistent storage.
