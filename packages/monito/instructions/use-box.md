## Box Environment

You run inside the Monito Docker container, using the `monito-box` image.
Ggets runs in a separate container, reachable at `http://ggets:8000` over the
shared internal network. The tree below shows your container, not the host.

```text
/
├── data/
│   ├── home/                         # HOME; persistent, read/write
│   │   └── .skiller/                 # Personal settings, secrets and runtime state
│   │       └── db/agent.db            # Run database
│   └── workspace/                    # Working directory; persistent, read/write
├── etc/monito/
│   ├── config.json                   # Runtime configuration; read-only host mount
│   └── monito.agente.json                    # Agent profile; read-only host mount
├── usr/local/lib/python3.12/site-packages/packages/
│   ├── monito/                       # Installed agent resources; read-only
│   │   ├── monito.yaml               # @monito
│   │   ├── system.md
│   │   └── instructions/
│   └── webhook/
│       └── webhook.yaml              # @webhook
└── tmp/                              # Temporary, size-limited; not persistent
```

### Installed CLIs in Monito

- `monito`: launch the Monito agent.
- `skiller`: run and manage flows, inputs, webhooks and the local server.
- `stui`: Skiller terminal interface.
- `python`, `python3`, `pip`: Python 3.12 and package installation in your own venvs.
- `curl`: HTTP requests.
- `ddgs`: web search and page extraction to Markdown.
- `git`: repository operations.
- `browser-harness`: control Chromium through CDP; see `browser-harness --help`.
- `chromium`: browser; `chromium-sandbox` provides sandbox support. The browser is not started automatically.
- `ps`, `pgrep`, `pkill`, `top`: process inspection and management (`procps`).
- `sh`, `bash`: shells, alongside standard Linux utilities.

`ggets` is installed in the Ggets container, not Monito; use its HTTP API from
Monito. `uv` and `pipx` are not installed by the Monito Dockerfile.

Chromium runs as a non-root user with its sandbox enabled under the supplied Compose
configuration. Do not use `--no-sandbox`.
