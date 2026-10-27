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

**Output:** an annotated Git tag `vX.Y.Z` (or a SemVer prerelease such as `v0.1.0-beta.1`).

1. `[admin]` selects the next semantic version.
2. `[dev]` creates `release/X.Y.Z` from `main` (or a SemVer prerelease such as `release/0.1.0-beta.1`), moves the accumulated `Unreleased` entries to a dated version section in `CHANGELOG.md`, creates a new empty `Unreleased` section, and updates `VERSION`, `packages/monito/VERSION`, and `packages/tools/VERSION`. Deployment version selection is an administrator decision, not release metadata.
3. `[dev]` squashes the release branch so the pull request contains exactly one commit.
4. `[dev]` opens a pull request to `main`.
5. `[ci]` rejects release pull requests with more than one commit; otherwise it verifies version consistency, changelog structure, tests, flows, and the container build.
6. `[admin]` reviews and merges the release preparation into `main`.
7. When the release PR is squash-merged, `[ci]` compares the merge commit tree with the validated release commit tree. If they match, `[ci]` creates the annotated tag `vX.Y.Z` on the merge commit, preserving any SemVer prerelease suffix.

The tag identifies the exact source used for publication. No deployment occurs in this workflow.

## Publish

**Purpose:** build and distribute artifacts after a release PR is merged.

**Input:** a merged `release/X.Y.Z` pull request.

**Output:** an immutable Git tag and artifacts available from registries.

1. `[ci]` checks that the squash-merge tree is identical to the release commit tree validated by CI.
2. `[ci]` verifies the release branch, `VERSION`, and Git tag. It creates the annotated tag `vX.Y.Z` on the merge commit before publication. A retry accepts an existing tag only when it points to the same commit.
3. `[ci]` builds and publishes both images from that commit, with the same version:
   - `ghcr.io/fredycampino/monito-box:X.Y.Z`
   - `ghcr.io/fredycampino/ggets:X.Y.Z`
4. The optional Android integration also publishes `ghcr.io/fredycampino/monito-mobile:X.Y.Z` from the same release, using `docker/Dockerfile.mobile`. Deployments enabling mobile control must wait for this image as well. Publication of the base deployment is complete only when both base images are available. Image pushes are not atomic: if one fails, retry the release publication before deployment. A Git tag alone does not prove both images exist.
5. Python distributions are `monito` (`packages/monito`) and `ggets` (`packages/tools`). CI builds wheels and source distributions to validate packaging; the current publication workflow does not upload them to PyPI or attach them to a GitHub release. They are installed in the container images. Standalone Python publication requires a separate approved policy and credentials; the legacy `sk-telegram` and `sk-cloudflared` packages are no longer release artifacts.

Production deployment must use the explicit release tag for both images, never `:latest` or `:dev`. No automatic deployment occurs after publication.

## Deploy

**Purpose:** run a selected, already published version in an environment.

**Input:** an image tag or digest, environment configuration, and persistent data.

**Output:** the selected version running and verified in that environment.

1. `[admin]` selects a successfully published release and confirms both versioned images exist.
2. `[admin]` prepares the distribution files and environment-specific configuration as described in [Versioned deployment](deployment.md). Set `IMAGE_PREFIX=ghcr.io/fredycampino/` and `RELEASE_VERSION` explicitly; preserve host paths, UID/GID, secrets and persistent data.
3. `[admin]` pulls both images before recreating either service, without building on the server.
4. `[admin]` verifies both containers, STUI access, `@monito`, `@webhook`, persistent state, Health and enabled integrations. Container startup does not resume listeners or start the Skiller webhook server automatically.
5. If verification fails, `[admin]` selects the previous known-good release and pulls/recreates both services together. Preserve data; check migration compatibility before rollback. A partial pull must not trigger recreation.

See [Versioned deployment](deployment.md) for commands. Deployment and rollback are explicit administrator actions, not CI side effects.

## Boundaries

- A feature or release pull request contains exactly one commit. `[ci]` rejects multi-commit pull requests.
- Feature pull requests add at least one entry to the top-level `Unreleased` changelog section; release pull requests turn those entries into the versioned release section.
- `[dev]` does not publish artifacts or deploy production environments.
- `[ci]` receives only the credentials needed for its assigned action.
- `[admin]` owns production secrets and deployment access.
- A release tag is immutable; a correction requires a new version.
- Docker images contain application code and fixed dependencies. User state, credentials, and databases remain outside the image in the deployment's persistent storage.
