# Local deployment

Run commands from the repository root. Docker Engine and Docker Compose are required.
Use `--env-file docker/compose.env` consistently for all Compose commands.
This guide builds local images. For published images, upgrades and rollback,
see [Versioned deployment](deployment.md).
`exec` uses the running container's existing environment; it does not reload it.

- `docker/compose.env`: Compose variables, including host UID/GID; not injected automatically.
- `docker/monito.env`: environment variables loaded into Monito through `env_file:`.
- `docker/ggets.env`: environment variables loaded into Ggets through `env_file:`.

## 1. Prepare

1. Compose settings: `docker/compose.env` must contain the deployment settings described in `docker/compose.env.example`, including the host UID/GID. Local builds use an empty `IMAGE_PREFIX` and `RELEASE_VERSION=dev`, not published release tags.
2. Container environment: `docker/monito.env` and `docker/ggets.env` must match the deployment.
3. Data layout: `data/` must contain the structure provided by `data-examples/`, including configuration, home, workspace, secrets and state directories. Existing settings, credentials and state must be preserved.
4. Application configuration: `data/monito/settings/monito.agente.json`, `data/monito/settings/config.json` and `data/ggets/config.json` must match the deployment, with listen addresses aligned with Compose. The Runtime and Ggets examples are templates: replace every `${...}` placeholder with deployment values before startup, using an integer for `GGETS_TELEGRAM_PORT`. Skiller does not expand these placeholders. Automated configuration generation is not implemented yet.
5. Credentials: the example placeholders must be replaced with valid credentials in `data/monito/home/.skiller/secrets/` and `data/ggets/secrets/`. Real credentials must remain outside Git, images and shell history.
6. Access: the configured container UID/GID must have the required access to configuration and persistent data. Ggets secrets and state directories require mode `0700`; secret files require `0600`. Monito's mounted configuration files must exist before startup; missing paths cause startup to fail rather than creating root-owned directories.

## 2. Build images

```bash
docker compose --env-file docker/compose.env build --no-cache
```

Images remain in the local Docker image store; this does not publish them.

## 3. Bring up services

```bash
docker compose --env-file docker/compose.env up -d --force-recreate
```

Compose creates or recreates containers as needed. `-d` runs them in the background.

## 4. Check status and logs

```bash
docker compose --env-file docker/compose.env ps
docker compose --env-file docker/compose.env logs --tail=50
```

A restarting container is not ready. Inspect its logs before opening a session.

## 5. Open a session

Open a shell in the running Monito container:

```bash
docker compose --env-file docker/compose.env exec monito sh
```

Open the interactive Skiller interface with Monito:

```bash
docker compose --env-file docker/compose.env exec monito skiller @monito
```

## 6. Check Ggets

```bash
docker compose --env-file docker/compose.env exec ggets ggets health check
```

Inside the Compose network, Ggets is available at `http://ggets:8000`.
Module help is at `GET /health/help`. Only the Telegram receiver is published to the host; the tools API is not.

## 7. Enable Skiller webhooks when needed

The container entrypoint starts the Skiller HTTP server and waits for health
before running the main command. It does not create or resume webhook listeners.
Verify server status:

```bash
docker compose --env-file docker/compose.env exec monito skiller server status
```

Verify access from Ggets, not just from inside Monito:

```bash
docker compose --env-file docker/compose.env exec ggets python -c 'import urllib.request; print(urllib.request.urlopen("http://monito:8001/health", timeout=5).status)'
```

Expect HTTP 200. The example assumes the default Skiller port. Its JSON listen
address must match Monito's internal IP; `127.0.0.1` inside Monito cannot receive
Ggets requests.

For Telegram, follow the packaged `use-telegram.md` procedure: obtain the
subscriber `run_id`, start `@webhook` in the same database, handle any
`WEBHOOK_WAIT_CONFLICT`, and register the consumer URL with GgTelegram only after
the listener is waiting. Keep Skiller on the private network: the current bridge
registers without authentication. Do not activate external integrations merely
as a health check.

## 8. Stop services

```bash
docker compose --env-file docker/compose.env down
```

The bind-mounted `data/` directory is preserved. Rebuild after code changes;
restart Ggets after changing its mounted configuration.

## Resource limits

`docker/compose.env` sets Monito's memory, CPU, process count, and `/tmp` size.
Defaults: 8 GiB memory, no extra swap, 8 CPUs, 256 processes, and 128 MiB `/tmp`.
Apply changes with `docker compose --env-file docker/compose.env up -d`.

See [Docker specification](docker-spec.md) for the deployment design.

## Ggets private data

Monito mounts its home, workspace, agent profile and runtime JSON, never the entire `data/` tree.
Ggets runs with the configured host UID/GID and alone mounts:
- `data/ggets/secrets` → `/run/secrets`, read-only (directory 0700, files 0600).
- `data/ggets/state` → `/data/telegram`, writable (directory 0700).

Both directories are excluded from Git and images. Telegram credential paths are
configured in `data/ggets/config.json`. Add the real public HTTPS `base_url`
before enabling Telegram; no public URL is assumed.

`GGETS_CONFIG_HOST_FILE` in `docker/compose.env` selects the host configuration file.
Default: `./data/ggets/config.json`. Remote deployments can select an absolute
path such as `/srv/ggets/config.json`. Inside the container, `GGETS_CONFIG_FILE`
remains `/etc/ggets/config.json`. Recreate Ggets after changing the host file path.

### Ggets host paths

Set these in the deployment's Compose env file; container paths stay unchanged:

| Variable | Local default | Container destination |
| --- | --- | --- |
| `GGETS_CONFIG_HOST_FILE` | `./data/ggets/config.json` | `/etc/ggets/config.json` (read-only) |
| `GGETS_ENV_HOST_FILE` | `./docker/ggets.env` | Loaded as container environment |
| `GGETS_SECRETS_HOST_DIR` | `./data/ggets/secrets` | `/run/secrets` (read-only) |
| `GGETS_STATE_HOST_DIR` | `./data/ggets/state` | `/data/telegram` (writable) |

Use absolute host paths for remote deployments. Relative paths resolve from the
Compose project directory, not the env file directory. Recreate Ggets after changes;
no image rebuild is needed.

### Monito host paths

| Variable | Local default | Container destination |
| --- | --- | --- |
| `MONITO_HOME_HOST_DIR` | `./data/monito/home` | `/data/home` (writable) |
| `MONITO_WORKSPACE_HOST_DIR` | `./data/monito/workspace` | `/data/workspace` (writable) |
| `MONITO_CONFIG_HOST_FILE` | `./data/monito/settings/config.json` | `/etc/monito/config.json` (read-only) |
| `MONITO_SETTINGS_HOST_DIR` | `./data/monito/settings` | Only `monito.agente.json`, mounted read-only at `/etc/monito/monito.agente.json` |

`SKILLER_RUNTIME_CONFIG_FILE=/etc/monito/config.json` selects the mounted runtime JSON.
Its `flow_paths` points to `/usr/local/lib/python3.12/site-packages/packages`,
a mirror of the repository resources: `monito/monito.yaml` and
`webhook/webhook.yaml`, resolved as `@monito` and `@webhook`.
The image does not generate deployment configuration. Set `webhooks.host` to
match `MONITO_INTERNAL_IP` and `webhooks.port` to the Skiller listener port
(default `8001`), so Ggets can reach it over the internal network. Restart the
Skiller server after changing its listening address.

The profile destination is `/etc/monito/monito.agente.json`, referenced directly by the
flow. The wheel does not include an agent profile.
Mounted configuration changes do not require rebuilding images. Start a new agent session to load profile changes; recreate containers when changing mount paths or environment variables. Close STUI sessions before recreating Monito.

## Network separation

| Access | Address | Configuration |
| --- | --- | --- |
| Monito → tools API | `http://ggets:8000` on `internal` | JSON `server.host=172.28.0.2` |
| Host tunnel → Telegram receiver | `http://127.0.0.1:8001` | Compose `GGETS_TELEGRAM_BIND_IP` and `GGETS_TELEGRAM_HOST_PORT` |
| Ggets → Skiller | `http://monito:8001` on `internal` | Monito JSON `webhooks.host=172.28.0.3`, `webhooks.port=8001` |
| Receiver inside Ggets | `172.29.0.2:8001` on `ingress` | JSON `telegram.receiver_host` and `receiver_port` |

Monito joins only `internal`; Ggets joins both networks. Neither server listens on
`0.0.0.0`. These are network names, not a Docker `internal: true` network: Ggets
still needs outbound access to Telegram and consumer webhooks. The ingress network
has gateway priority so Docker publishes the receiver port on that interface.
Requires Compose support for `gw_priority` (2.33.1 or later).

Set subnets, static IPs and published ports in the deployment Compose env file.
Keep the JSON listen addresses/ports aligned with those values. Choose subnets
that do not overlap existing host, VPN or Docker networks. Recreate both services
after network changes; no image rebuild is needed. Close STUI sessions first.

Cloudflared running on the host targets `http://127.0.0.1:8001`. Its public HTTPS
URL goes in `telegram.base_url`; the tunnel forwards `/telegram/webhook` unchanged.
The receiver only starts when the required Telegram configuration is present.
A webhook request without the correct secret must be rejected.
