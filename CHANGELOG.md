# Changelog

All notable changes to Monito are documented in this file.

## Unreleased

- Nothing yet.

## 0.1.0-beta.8 - 2026-10-23

### Added

- Add an optional USB ADB server with persistent authorization keys and a private client connection from Monito; install ADB in the Monito image.

### Fixed

- Update Skiller to 0.1.0-beta.45, removing the shell denylist that falsely blocked Telegram replies containing literal text such as the Spanish word “su”, while retaining configured tool permissions.

## 0.1.0-beta.7 - 2026-10-20

### Fixed

- Keep the webhook listener waiting after failed subscriber deliveries, with a 30-second command timeout inside the 45-second step limit and no retries.

- Execute Ggets CLI operations without starting module listeners, avoiding Telegram receiver port conflicts while the HTTP server is running.

## 0.1.0-beta.6 - 2026-10-20

### Changed

- Increase the default Monito container budget to 8 GB RAM and 8 CPUs, without extra swap.

### Added

- Preinstall DDGS 9.16.0 for web search and Markdown extraction without a workspace venv.

- Install Browser Harness 0.1.13 in the Monito image for Chromium control through CDP.

- Include Chromium with namespace sandbox support using a dedicated seccomp profile and only the SYS_CHROOT capability.

- Include Git in the Monito image for repository operations.
- Add Nexo as an independent host development agent, without changing Monito Box or migrating existing sessions.

### Removed

- Remove the legacy host development agent in `monito/`; Nexo replaces it while preserving historical context and run records.

### Fixed

- Start the Skiller webhook server through the Monito container entrypoint on every startup and restart; leave status verification to the agent.

## 0.1.0-beta.5 - 2026-10-18

### Added

- Introduce Ggets with independent Health and Telegram modules exposed through CLI and HTTP.
- Add a generic webhook listener that forwards labeled payloads to a subscriber run.
- Document Telegram integration, module configuration, deployment and known lifecycle limitations.

### Changed

- Provide a data-examples deployment layout and a read-only Monito profile at /etc/monito/agent.json.
- Refresh Box, package installation and internet search instructions; define explicit webhook listener handover.

- Isolate the tools API and Telegram ingress on separate container networks with interface-specific listeners.
- Mount Monito runtime configuration and agent settings from the host; preserve the package resource layout in the wheel.
- Use one Compose definition for local builds and versioned deployment of the Monito/Ggets image pair.
- Replace standalone Telegram tooling with Ggets operations while retaining feature/release approval and single-commit checks.

### Fixed

- Deliver webhook notifications from /data/workspace so resumed agents retain an authorized working directory.

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
