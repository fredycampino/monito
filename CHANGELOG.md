# Changelog

All notable changes to Monito are documented in this file.

## 0.1.0 - 2026-10-09

### Added

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
