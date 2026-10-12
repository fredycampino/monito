# Changelog

All notable changes to Monito are documented in this file.

## Unreleased

- Nothing yet.

## 0.1.0-beta.4 - 2026-10-12

### Changed

- Upgrade Monito Box to Skiller beta.43, including read-only-safe authentication.
- Select the Monito agent profile explicitly through `config.file` and `MONITO_AGENT_CONFIG_FILE`, keeping development and Box profiles separate.

## 0.1.0-beta.3 - 2026-10-11

### Added

- Versioned server deployment manifest for Monito Box with a non-root service identity and persistent `/data` storage.
- Release validation now requires the deploy image version to match `VERSION`.

### Fixed

- Use Monito Box's flow-local agent override without applying it globally to every Skiller agent.
- Create and push the immutable release tag before publishing its container image.
- Configure the GitHub Actions tagger identity for annotated release tags.

## 0.1.0-beta.2 - 2026-10-11

### Added

- Automated publish workflow that verifies squash-merge tree identity before creating a release tag and publishing Monito Box to GHCR.

### Fixed

- Allow manually dispatched publish retries to resolve their merged release pull request from a release version.

## 0.1.0-beta.1 - 2026-10-11

### Added

- Unified pull-request CI validation with local feature and release validators.
- Monito agent flow with interactive task handling and guidance for Telegram and Cloudflare tunnels.
- `sk-telegram` CLI for receiving Telegram webhooks, sending responses, checking status, and managing webhook configuration.
- `sk-cloudflared` CLI for Cloudflare authentication and tunnel lifecycle management.
- Tests for the Telegram bridge/webhook flow and Cloudflare CLI, login, and tunnel operations.
- Monito Box: a Docker/OCI runtime with Skiller `0.1.0-beta.42`, the bundled `@monito` flow, a non-root default user, and read-only root filesystem.
- Docker Compose development deployment with host-owned persistent state under `data/`, a temporary `/tmp`, and terminal colour propagation for STUI.
- Documentation for architecture, Telegram/Cloudflare tools, and building and operating Monito Box.

### Security

- Keep local credentials, Skiller state, SQLite data, Compose identity settings, Python environments, and build artifacts out of version control and the Docker build context.
- Run Monito Box without Linux capabilities and without writable image layers; the host bind mount is limited to `data/`.

### Known limitations

- The agent's unrestricted tool profile inside Monito Box can read its own persisted LLM credentials under `data/home/.skiller/secrets/`. This is an accepted temporary trade-off; credentials are rotatable and no more sensitive host secrets, Docker socket, or privileged mounts are exposed.
