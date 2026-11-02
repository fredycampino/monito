# Docker Specification

Current Compose architecture. See [Local deployment](local-deployment.md) for
setup and [Versioned deployment](deployment.md) for upgrades and rollback.

## 1. Architecture

Simplified configured architecture (not a snapshot of running containers).
The base Compose starts Monito and Ggets; the mobile overlay adds Mobile.

```text
                           LINUX HOST
  User terminal                                  Public Telegram webhook
       | docker compose exec                               |
       v                                          Host tunnel (HTTPS)
+------------------------------ DOCKER ---------------------|-----------+
|                                                          v           |
|                                             127.0.0.1:8001 published  |
|                                                          |           |
|  +----------------------+      +-------------------------v--------+   |
|  | MONITO               |      | GGETS                            |   |
|  | Agent + Skiller      |----->| Tools API :8000                  |   |
|  | STUI + webhook :8001 |<-----| Event delivery / Telegram       |   |
|  | ADB client + HTTP    |      | Receiver :8001 (ingress network) |   |
|  +----------+-----------+      +----------------------------------+   |
|             |                   Monito <-> Ggets: internal network   |
|             |                                                        |
|             | Dedicated mobile network (internal: true)               |
|             | ADB :5037 / Appium HTTP :4723                            |
|             v                                                        |
|  +----------------------+                                            |
|  | MOBILE (optional)    |       No published ADB/Appium ports          |
|  | Appium + UiAutomator2|       No Ggets access to mobile network      |
|  | Local ADB server    |                                            |
|  +----------+-----------+                                            |
+-------------|--------------------------------------------------------+
              | /dev/bus/usb (only Mobile)
              v
       +--------------+
       | ANDROID PHONE|
       | Apps + UI    |
       +--------------+

  HOST PERSISTENT STORAGE (bind mounts, separate from images)
  Monito <- HOME (Skiller DB/settings), workspace, read-only configuration
  Ggets  <- Telegram state, secrets, read-only configuration
  Mobile <- ADB HOME/.android (authorization keys, reused across recreations)

  OUTBOUND SERVICES
  Monito -> LLM provider             Ggets -> Telegram API
```

The tools API request and event delivery are separate directions: Monito calls
Ggets; Ggets sends events to Skiller, which routes them through `@webhook` to the
subscriber run. Mobile controls the phone through its own ADB server; Monito
can use either the remote ADB client or Appium's HTTP API.

Default networks are `internal` (`172.28.0.0/24`) and `ingress`
(`172.29.0.0/24`). Ggets joins both; Monito joins `internal` and, when enabled,
`mobile`. Only Monito and Mobile join the dedicated `mobile` network.
The network named `internal` is **not** declared with Docker's `internal: true`,
so outbound provider access remains available. The `mobile` network is isolated
with `internal: true`. Addresses and ports are configurable defaults.

ADB authorization persists in the existing host directory selected by
`ADB_HOME_HOST_DIR`, mounted as `/data/home` in Mobile. It is not inherited from
an image or from Monito's HOME. Appium caches live in temporary storage and do
not require another persistent volume. See [Mobile setup](android-mobile.md).

## 2. Images and resources

Image names use `${IMAGE_PREFIX}` (empty locally,
`ghcr.io/fredycampino/` for published deployments) and `${RELEASE_VERSION}`
(`dev` locally; explicit published version without `v` in production).
Images contain code and dependencies, not personal settings, secrets or state.
All services use non-root execution, read-only root filesystems and
`restart: unless-stopped`. Host ownership must match `HOST_UID`/`HOST_GID`
(default `10001:10001`).

### Monito — agent and Skiller runtime

Image: `${IMAGE_PREFIX}monito-box:${RELEASE_VERSION}`.
Build: `docker/Dockerfile.monito`; service: `monito` in `compose.yaml`.
Includes Python, Monito, Skiller, ADB client, curl, Git, procps, Chromium,
Browser Harness 0.1.13 and DDGS 9.16.0. Starts the Skiller server, then remains
available for interactive STUI; it does not automatically start agent runs.

Network: `internal`, plus `mobile` when enabled. Calls Ggets at
`http://ggets:8000`, receives webhooks on `monito:8001`, and calls the LLM
provider outbound. No published ports. With mobile enabled, uses ADB on
`mobile:5037` and Appium on `mobile:4723`; no USB mount.

Container filesystem (`RW` = writable bind mount; `RO` = read-only):

```text
/data/home/                         RW <- MONITO_HOME_HOST_DIR
  .skiller/db/agent.db              Persistent runtime database
  .skiller/                        Personal Skiller settings and state
/data/workspace/                    RW <- MONITO_WORKSPACE_HOST_DIR
/etc/monito/agent.json              RO <- MONITO_SETTINGS_HOST_DIR/agent.json
/etc/monito/config.json             RO <- MONITO_CONFIG_HOST_FILE
/usr/local/lib/python3.12/site-packages/packages/  Installed flow resources
/tmp/                              Temporary tmpfs
```

Runtime variables: `HOME=/data/home`,
`SKILLER_DB_PATH=/data/home/.skiller/db/agent.db`,
`SKILLER_RUNTIME_CONFIG_FILE=/etc/monito/config.json` (from `docker/monito.env`);
`TERM` and `COLORTERM` come from Compose. The mobile overlay adds
`ADB_SERVER_SOCKET=tcp:mobile:5037` and `APPIUM_URL=http://mobile:4723`.
The flow explicitly loads `/etc/monito/agent.json`; runtime `flow_paths` uses the
installed packages directory for `@monito` and `@webhook`. This fixed path remains
a limitation documented in [Flow path TODO](todo/fix-flows-path.md).

Compose variables: `MONITO_HOME_HOST_DIR`, `MONITO_WORKSPACE_HOST_DIR`,
`MONITO_SETTINGS_HOST_DIR`, `MONITO_CONFIG_HOST_FILE`, `MONITO_INTERNAL_IP`;
`MONITO_MEMORY_LIMIT=8g`, `MONITO_CPU_LIMIT=8`, `MONITO_PIDS_LIMIT=256`,
`MONITO_TMPFS_SIZE=128m`. Swap limit equals memory limit (no extra swap).

### Ggets — tools API and Telegram integration

Image: `${IMAGE_PREFIX}ggets:${RELEASE_VERSION}`.
Build: `docker/Dockerfile.ggets`; service: `ggets` in `compose.yaml`.
Includes Python and Ggets with Health/Telegram modules. Runs `ggets serve`;
it does not contain Monito or manage its agent lifecycle.

Network: `internal` for the API (`ggets:8000`) and delivery to Skiller
(`monito:8001`); `ingress` for the Telegram receiver (`:8001`) and outbound
Telegram API access. Only the receiver is published, by default at host
`127.0.0.1:8001`. No connection to the `mobile` network.

```text
/etc/ggets/config.json             RO <- GGETS_CONFIG_HOST_FILE
/run/secrets/                      RO <- GGETS_SECRETS_HOST_DIR
/data/telegram/                    RW <- GGETS_STATE_HOST_DIR
/tmp/                              Temporary tmpfs
```

Runtime variable: `GGETS_CONFIG_FILE=/etc/ggets/config.json`, loaded from
`GGETS_ENV_HOST_FILE` (default `docker/ggets.env`). Listen addresses, modules and
secret references are configured in the mounted JSON, not generated by Compose.

Compose variables: `GGETS_CONFIG_HOST_FILE`, `GGETS_ENV_HOST_FILE`,
`GGETS_SECRETS_HOST_DIR`, `GGETS_STATE_HOST_DIR`, `GGETS_INTERNAL_IP`,
`GGETS_TELEGRAM_IP`, `GGETS_TELEGRAM_BIND_IP=127.0.0.1`,
`GGETS_TELEGRAM_HOST_PORT=8001`, `GGETS_TELEGRAM_PORT=8001`.
No service-specific CPU/memory/PID limits are currently configured.

### Mobile — USB Android control (optional)

Image: `${IMAGE_PREFIX}monito-mobile:${RELEASE_VERSION}`.
Build: `docker/Dockerfile.mobile`; service: `mobile` in
`docker/compose.mobile.yaml`. Includes Node 22.23.4, Java 17 runtime, Python,
Debian ADB, Appium 3.9.0 and UiAutomator2 8.7.2. No full Android SDK or Build
Tools. Dependencies are installed during the build using the appium-lab lockfile.
Both servers are supervised; either exiting stops the container. Health checks
query both services without requiring a connected phone.

Network: only `mobile` (`internal: true`). Accepts Monito's ADB requests on
`:5037` and Appium HTTP on `:4723`; neither port is published. ADB talks to the
phone through the USB mount. No Ggets access or external network is required.

```text
/data/home/                         RW <- ADB_HOME_HOST_DIR
  .android/adbkey                   Persistent private ADB authorization key
  .android/adbkey.pub               Persistent public ADB authorization key
/dev/bus/usb/                       Host USB device tree (group-controlled)
/opt/mobile/                       RO installed Node dependencies + manifest
/usr/lib/android-sdk/platform-tools/adb  RO Debian ADB executable
/usr/local/lib/mobile/              RO supervisor and healthcheck scripts
/tmp/mobile/                       Temporary writable project metadata
/tmp/mobile-cache/                 Temporary Appium extension cache
```

Runtime variables: `HOME=/data/home`, `ANDROID_HOME=/usr/lib/android-sdk`.
The latter refers to Debian ADB's directory, not an installed full SDK or a host
SDK mount. The supervisor clears inherited `APPIUM_HOME` and `ADB_SERVER_SOCKET`
to use the packaged driver and local ADB server.

Compose variables: `ADB_HOME_HOST_DIR` (default `./data/adb/home`, reuses the
existing authorization storage) and required `ADB_USB_GID` (host USB access
group). The service adds that group and USB device rules, without privileged
mode. PID limit: 256; `/tmp` is tmpfs. No explicit CPU/memory limits are configured.
The phone's `/data/local/tmp/monito` is a separate remote exchange directory,
not a container mount. See [Mobile setup](android-mobile.md).

Builds and publication do not deploy containers. Production must pull all
selected images at the same explicit release before recreation; no `latest` or
server-side builds. Preserve persistent mounts during upgrades and rollback.

## 3. Startup

- Monito's entrypoint runs `skiller server start`, then executes `sleep infinity`
  under Docker init for interactive Skiller use. A failed startup exits nonzero.
- Ggets runs `ggets serve` in the foreground.
- Both use `restart: unless-stopped`.
- Startup does not install dependencies or create user configuration.
- Each container start starts the Skiller webhook server and waits for HTTP health.
  It does not create listeners or resume agent runs automatically.
- A later server failure is not supervised while `sleep infinity` remains alive.
- Monito does not administer the Ggets container.

## 4. Configuration and mounts

Host paths below are defaults, configurable in `docker/compose.env`:

| Service | Host source | Container target | Access |
| --- | --- | --- | --- |
| Monito | `data/monito/home` | `/data/home` | Read/write |
| Monito | `data/monito/workspace` | `/data/workspace` | Read/write |
| Monito | `data/monito/settings/agent.json` | `/etc/monito/agent.json` | Read-only |
| Monito | `data/monito/settings/config.json` | `/etc/monito/config.json` | Read-only |
| Ggets | `data/ggets/config.json` | `/etc/ggets/config.json` | Read-only |
| Ggets | `data/ggets/secrets` | `/run/secrets` | Read-only |
| Ggets | `data/ggets/state` | `/data/telegram` | Read/write |

- `MONITO_CONFIG_HOST_FILE` selects the host runtime JSON;
  `SKILLER_RUNTIME_CONFIG_FILE=/etc/monito/config.json` selects it in Monito.
  It configures `flow_paths` and the Skiller webhook server address.
- The mounted `agent.json` configures the Monito agent, separately from runtime
  configuration. Personal Skiller settings/state also reside under `/data/home`.
- `GGETS_CONFIG_HOST_FILE` selects the host JSON;
  `GGETS_CONFIG_FILE` selects `/etc/ggets/config.json` inside Ggets.
- Ggets JSON has a `server` section and module-specific sections. Each module
  receives its own configuration. Secrets are referenced by file path.
- The `data-examples/` tree mirrors `data/` with final configuration filenames and
  empty persistent directories; copy and complete it before first startup.
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
- Monito adds only `SYS_CHROOT` to its otherwise empty capability bounding set
  and uses `docker/chromium-seccomp.json` to allow Chromium's namespace sandbox.
  It remains non-root with `no-new-privileges` and the default AppArmor profile;
  do not launch Chromium with `--no-sandbox`.
- The vendored seccomp profile comes from
  [Playwright](https://github.com/microsoft/playwright/blob/main/utils/docker/seccomp_profile.json):
  Docker's default-style allowlist with additional `clone`, `setns`, and `unshare`
  permissions. Review upstream changes before updating it. Ship this file with Compose.
- Chromium and Browser Harness are installed but the browser is not automatically
  started. Browser lifecycle integration is separate work.
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

## 9. Optional Android USB access

See [Android mobile](android-mobile.md) for the optional `docker/compose.mobile.yaml`
override, server HOME persistence, host USB permissions and verification.
The base deployment remains two services; mobile control is enabled explicitly.
