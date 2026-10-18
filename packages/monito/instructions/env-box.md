## Box Environment

Before using these paths, check the current directory and whether `/.dockerenv`
exists. This layout applies to the Monito container, not host execution.

| Container path | Purpose | Access |
| --- | --- | --- |
| `/data/home` | HOME, personal configuration and runtime state | Read/write, persistent |
| `/data/workspace` | Working files and shell working directory | Read/write, persistent |
| `/etc/monito/config.json` | Runtime configuration, including `flow_paths` | Read-only |
| `/usr/local/lib/python3.12/site-packages/packages` | Installed flow resources, mirroring repository `packages/` | Read-only |

- Home and workspace are separate host mounts, normally `data/monito/home` and
  `data/monito/workspace`. The host's entire `data/` directory is not mounted.
- Runtime configuration is selected by `AGENT_RUNTIME_CONFIG_FILE`. Its host
  source is configurable with `MONITO_CONFIG_HOST_FILE`; the local default is
  `data/monito/settings/config.json`.
- The flow resource tree contains `monito/monito.yaml`, its prompts and
  instructions, and `webhook/webhook.yaml`. Resolve them as `@monito` and
  `@webhook` through the configured `flow_paths`.
- The Monito agent profile is mounted read-only at
  `/usr/local/lib/python3.12/site-packages/packages/monito/agent.json`, normally
  from `data/monito/settings/agent.json` on the host.
- `AGENT_DB_PATH=/data/home/.skiller/db/agent.db` selects the run database. A
  listener forwarding input to another run must use that same database.
- Store working files in `/data/workspace`, not in the installation directory.
  The image filesystem is read-only; `/tmp` is temporary, size-limited storage.
- Do not read or disclose secrets, or manually modify the live runtime database.
- Ggets is a separate container, reachable at `http://ggets:8000` on the internal
  Docker network. Monito does not mount Ggets configuration, secrets or state.
- The Telegram receiver uses a separate ingress network; Monito must not call it
  directly. For integration, follow `use-telegram.md`: GgTelegram forwards events
  to Monito's Skiller webhook server over the internal network.
- Do not assume access to host repositories or files outside the configured
  mounts. A server bound only to loopback inside Monito is not reachable from
  Ggets; verify its listening address and port before registering its URL.
