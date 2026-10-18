# Docker Specification

Current Compose architecture. See [Local deployment](local-deployment.md) for
setup and [Versioned deployment](deployment.md) for upgrades and rollback.

## 1. Architecture

```text
Host tunnel (external infrastructure)
    |
    v
127.0.0.1:8001 (published receiver port)
    |
    v
Ingress network: 172.29.0.0/24
    Ggets Telegram receiver: 172.29.0.2:8001
    |
    | Same Ggets container, separate listening interfaces
    |
Internal network: 172.28.0.0/24
    Ggets API: 172.28.0.2:8000 <--- Monito: 172.28.0.3
    Ggets event delivery ----------> Skiller: monito:8001
                                        |
                                   @webhook listener
                                        |
                                   Subscriber run

User terminal ---> Monito / Skiller STUI
Monito ----------> LLM provider
Ggets -----------> Telegram API
```

Addresses and ports above are configurable defaults. Monito joins only the
internal network; Ggets joins both. The internal network is not declared with
Docker's `internal: true`: outbound provider access remains available.

## 2. Images and resources

- **Monito:** Python, Monito, Skiller, curl, CA certificates and procps.
- **Ggets:** Python, the Ggets HTTP manager and registered Health/Telegram modules.
- Neither image installs the other product. Images contain no personal settings,
  secrets or runtime state.
- The Monito wheel preserves the `packages/monito/` and `packages/webhook/`
  resource layout. Runtime `flow_paths` points to
  `/usr/local/lib/python3.12/site-packages/packages`; references are `@monito`
  and `@webhook`. This installation-specific path remains a documented limitation
  in [Flow path TODO](todo/fix-flows-path.md).

One root `compose.yaml` defines both services, networks, mounts and local build
contexts. `docker/Dockerfile.monito` and `docker/Dockerfile.ggets` build local
images. Both image names use shared Compose variables:

- Local defaults: empty `IMAGE_PREFIX`, `RELEASE_VERSION=dev`.
- Published deployment: `IMAGE_PREFIX=ghcr.io/fredycampino/` and an explicit
  `RELEASE_VERSION`, without the Git tag's leading `v`.
- Images: `${IMAGE_PREFIX}monito-box:${RELEASE_VERSION}` and
  `${IMAGE_PREFIX}ggets:${RELEASE_VERSION}`.

Deployment pulls both images successfully before `up -d --no-build`; it does not
build on the server or use `latest`. Rollback selects the previous shared version,
subject to persistent-data compatibility. CI/release and deployment remain
separate responsibilities.

## 3. Startup

- Monito runs `sleep infinity` under Docker init for interactive Skiller use.
- Ggets runs `ggets serve` in the foreground.
- Both use `restart: unless-stopped`.
- Startup does not install dependencies or create user configuration.
- Container startup does not start the Skiller webhook server, create listeners,
  or resume agent runs automatically. Start/check these explicitly when needed.
- Monito does not administer the Ggets container.

## 4. Configuration and mounts

Host paths below are defaults, configurable in `docker/compose.env`:

| Service | Host source | Container target | Access |
| --- | --- | --- | --- |
| Monito | `data/monito/home` | `/data/home` | Read/write |
| Monito | `data/monito/workspace` | `/data/workspace` | Read/write |
| Monito | `data/monito/settings/agent.json` | `/usr/local/lib/python3.12/site-packages/packages/monito/agent.json` | Read-only |
| Monito | `data/monito/settings/config.json` | `/etc/monito/config.json` | Read-only |
| Ggets | `data/ggets/config.json` | `/etc/ggets/config.json` | Read-only |
| Ggets | `data/ggets/secrets` | `/run/secrets` | Read-only |
| Ggets | `data/ggets/state` | `/data/telegram` | Read/write |

- `MONITO_CONFIG_HOST_FILE` selects the host runtime JSON;
  `AGENT_RUNTIME_CONFIG_FILE=/etc/monito/config.json` selects it in Monito.
  It configures `flow_paths` and the Skiller webhook server address.
- The mounted `agent.json` configures the Monito agent, separately from runtime
  configuration. Personal Skiller settings/state also reside under `/data/home`.
- `GGETS_CONFIG_HOST_FILE` selects the host JSON;
  `GGETS_CONFIG_FILE` selects `/etc/ggets/config.json` inside Ggets.
- Ggets JSON has a `server` section and module-specific sections. Each module
  receives its own configuration. Secrets are referenced by file path.
- JSON examples live in `docker/`; prepare actual host files before startup.
  Startup must not overwrite existing settings or secrets.
- Compose interpolation uses `--env-file docker/compose.env`. Container variables
  come from `docker/monito.env` and the file selected by `GGETS_ENV_HOST_FILE`
  (default `docker/ggets.env`). Applications do not load these env files themselves.

## 5. Persistence

- Monito's database is `/data/home/.skiller/db/agent.db`. Do not manually modify
  a live database or expose its secrets.
- Workspace files belong in `/data/workspace`; home contains personal state.
- Telegram state persists under `/data/telegram`; Health needs no persistent state.
- `/tmp` is temporary. Recreating containers must preserve bind-mounted data.
- Startup performs no automatic data migration or deletion. Back up state before
  upgrades and check compatibility before rollback.

## 6. Networking

- Monito accesses the tools API at `http://ggets:8000` over the internal network.
- Ggets API binds only to `GGETS_INTERNAL_IP` (default `172.28.0.2`);
  Telegram's receiver binds only to `GGETS_TELEGRAM_IP` (`172.29.0.2`).
  Neither uses `0.0.0.0` in this deployment.
- Only the Telegram receiver is published, by default as
  `127.0.0.1:8001:8001`. The API and Monito server have no published host ports.
- A host-run tunnel targets `http://127.0.0.1:8001`. Public DNS, HTTPS and
  tunnel management are deployment infrastructure, not agent responsibilities.
- Skiller listens on Monito's internal IP (`172.28.0.3:8001` by default).
  Ggets delivers to `http://monito:8001/webhooks/<webhook>/<key>`.
  This consumer URL is distinct from Ggets' public Telegram webhook URL.
- Compose IP/subnet/port variables and JSON listen addresses must agree;
  changing Compose variables alone does not update JSON files.

## 7. Security

- Non-root processes, read-only image filesystems, dropped capabilities and
  `no-new-privileges`. Only mounted writable state/workspace and temporary
  storage are writable; host ownership must permit the selected UID/GID.
- Do not mount the Docker socket or the entire host filesystem.
- Provider secrets are mounted only in Ggets. Monito holds credentials required
  for its own operation, including its LLM provider.
- Ggets optionally authenticates its API with `server.token_file`; an authenticated
  client must also have access to the token through an explicitly provisioned mount.
- Telegram-to-Ggets webhook validation is separate from Ggets-to-Skiller
  authentication. The current forwarding integration uses Skiller `auth: none`;
  it does not provide token/signature authentication on that internal hop.
- Network separation is not authentication or a general guarantee against
  container escape. Modules inside the Ggets process are not mutually isolated.
- Do not log secrets; log retention is an operational responsibility.

## 8. Verification

- Validate Compose for local and published image selection. Build locally; pull
  published images for deployment, keeping both services on the same version.
- Check non-root execution, mount permissions, read-only settings and persistence
  after recreation.
- Check `@monito` and `@webhook` resolution and interactive STUI access.
- Check `POST /health/check` with `{}` from Monito. This checks Ggets availability,
  not external providers.
- Check that Monito cannot reach the ingress receiver and that only the receiver
  is published on host loopback. Unauthenticated receiver requests must be rejected.
- When enabled, start/check the Skiller server and verify its reachability from
  Ggets. Test event delivery separately; do not register external integrations as
  a routine health check.
- Verify configured API authentication and absence of tool provider secrets in
  Monito. Structural checks alone do not certify the deployment's security.
