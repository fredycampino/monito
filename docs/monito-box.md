# Monito Box

`monito-box` is the OCI image used to run Monito. It contains a fixed Skiller runtime and the Monito flow. The application is installed in `/opt/monito/`; mutable user state is deliberately outside the image.

## Contents

The image is based on `python:3.12-slim` and installs `skiller==0.1.0-beta.42` from PyPI. It runs as the unprivileged `monito` user (UID and GID `10001`) by default, starts the Skiller CLI by default, and bundles the `@monito` flow under `/opt/monito/monito/`.

Skiller is pinned deliberately. A published image must always identify the exact runtime it contains. Updating Skiller means changing the pin, validating compatibility, and publishing a new Monito Box image.

## Filesystem model

```text
/opt/monito/  application flows and instructions included in the image
/data/        persistent state, bind-mounted from the host
/tmp/         temporary files, backed by Compose tmpfs and discarded
```

Compose mounts the container root filesystem read-only and supplies `/tmp` as a temporary in-memory filesystem. Monito may read its installed instructions from `/opt/monito/`; persistent writes go under `/data`, with `/data/workspace/` intended for user artefacts. Skiller configuration, provider credentials, and its SQLite DB are all kept under `/data`.

## Build and verify

Build a local development image from the repository root:

```bash
docker build --tag monito-box:dev .
docker run --rm monito-box:dev --version
```

The default command shows Skiller help:

```bash
docker run --rm monito-box:dev
```

The image has no application state and exposes no port. Compose selects the bundled `agent.box.json` through `AGENT_AGENT_CONFIG_FILE`; it enables unrestricted Skiller `shell` and `files` tools inside the container while leaving the provider and model selected during interactive onboarding in persistent user configuration.

## Local Compose state

`compose.yaml` provides one idle box container that can be entered interactively. It persists all mutable state in the repository's `data/` directory, which is a bind mount rather than a Docker-managed volume.

Create the untracked Compose identity file with your numeric host identity:

```bash
cp compose.env.example compose.env
# Edit HOST_UID and HOST_GID, or generate it directly:
printf 'HOST_UID=%s\nHOST_GID=%s\n' "$(id -u)" "$(id -g)" > compose.env
```

Create the host-owned state directory, then start the box:

```bash
mkdir -p data/workspace
docker compose --env-file compose.env up --detach --build
```

Open the interactive Skiller UI and complete its normal onboarding:

```bash
docker compose --env-file compose.env exec box stui
```

Run Monito directly:

```bash
docker compose --env-file compose.env exec box skiller @monito
```

The image's default user is `monito` (`10001:10001`), but Compose overrides it with `HOST_UID:HOST_GID`. Therefore files created under the bind mount belong to the host user operating the box. Compose also passes `TERM` and `COLORTERM` (with `xterm-256color` and `truecolor` fallbacks) so the Textual STUI keeps the terminal's color capability.

After onboarding, state is visible on the host:

```text
data/home/.skiller/settings/providers.json
data/home/.skiller/secrets/
data/home/.skiller/runtime/
data/skiller/agent.db
data/workspace/
```

`data/home` is the container's `HOME`; `data/skiller/agent.db` is selected through `AGENT_DB_PATH`. Do not commit `data/` or `compose.env`. Back up these files, but do not manually modify the SQLite database while Skiller is running.

Stop the box without deleting the persistent state:

```bash
docker compose --env-file compose.env down
```

## Distribution

The Dockerfile describes image contents, not its registry name. A release pipeline can publish the same image under an OCI reference such as:

```text
ghcr.io/<owner>/monito-box:<version>
```
