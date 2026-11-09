# Installation workflow

Status: implemented by `install` and `scripts/install_helper.py`; isolated unit and mocked-Docker tests cover the workflow. A full live installation is not part of the automated checks.

Goal: install Monito and Ggets from scratch with one command, using a published version without manually copying examples or editing internal paths.

Interface: `./install --version <version> --dir <directory>`.

Scope: new installations only. Does not upgrade installations, install Docker, select a provider/model, or configure credentials, tunnels, Telegram or Android. Services can be healthy before the agent is ready for conversations.

## 1. Accept version and destination

Validate an explicit version, rejecting `latest` and `dev`, and resolve the destination to an absolute path. Keep the Compose project name stable throughout installation.

## 2. Check prerequisites

Required host prerequisites and checks:

| Requirement | Check | Failure message |
| --- | --- | --- |
| Linux host | Host platform is Linux. Other platforms are outside this first version's scope. | `ERROR [platform]: Linux is required.` |
| POSIX shell and Python 3.12+ | The entry point runs with `/bin/sh`; `python3` is available and its version is at least 3.12. The helper uses only the standard library. | `ERROR [python]: Python 3.12+ is required; install it and retry.` |
| Docker CLI | `docker` is available on PATH. | `ERROR [docker-cli]: Docker CLI was not found; install Docker Engine and retry.` |
| Accessible local Docker Engine | `docker info` succeeds directly or through the authorized sudo fallback below; the active endpoint uses a local Unix socket and the daemon runs Linux containers. Remote daemons are unsupported because deployment paths are local bind mounts. | `ERROR [docker-engine]: A local Linux Docker Engine is required. Check the Docker context, daemon and socket permissions.` |
| Docker Compose plugin 2.33.1+ | `docker compose version --short` reports at least 2.33.1, required for `gw_priority`. | `ERROR [compose]: Docker Compose plugin 2.33.1+ is required; install or upgrade it and retry.` |
| Writable destination | The destination, or its nearest existing parent, is a writable and searchable directory for the current user. | `ERROR [destination]: Cannot create files under <path>; choose a writable directory or correct its permissions.` |
| Writable temporary storage | Create and remove a temporary file and directory using the system temporary directory. | `ERROR [temporary-directory]: Cannot create temporary files under <path>; check TMPDIR and its permissions.` |

Docker privilege handling happens during these checks, before downloads or deployment changes:

- Try `docker info` as the current user first. Request elevation only when access fails because of socket permissions, not for an unavailable daemon or an unsupported endpoint.
- Explain: `Docker requires elevated permissions. Authorize sudo for Docker commands only? [y/N]`. On approval, use `sudo -v` to authenticate through the terminal, then verify Docker access with sudo against the same local socket. Do not silently switch to root's Docker context.
- If successful, print `OK [docker-engine]: Local Docker Engine accessible with sudo.` and use the same elevated Docker invocation for all subsequent Docker and Compose commands, including the Compose version check. Keep file generation, downloads and the rest of the installer running as the original user.
- If sudo is unavailable, authorization is declined, authentication fails or no interactive terminal is available, stop with `ERROR [docker-permissions]: Docker access requires sudo authorization; rerun interactively or grant the current user Docker access.` Never read or store the password in the installer.
- Reuse sudo's credential cache; if it expires and authentication is required again, explain why before requesting it. Do not promise that the operating system will prompt only once.

No host Git, curl, tar, pip or third-party Python packages are required. Downloads and extraction use Python's standard library. Network access to the source archive host and image registry is required in steps 4 and 6; actual download failures are reported there rather than inferred from a connectivity probe.

Print one result per check: `OK [<check>]: <summary>` or the corresponding `ERROR` message above. On success, finish with `Prerequisites passed.` and continue. On failure, report all checks that can still run, finish with `Prerequisites failed; installation stopped.`, and exit with status 1 before downloading files, creating deployment data or starting containers. Do not install dependencies, change Docker contexts or alter permissions automatically. Invoke sudo only for the explicitly authorized Docker fallback above; never run the entire installer with sudo.

## 3. Confirm a new installation

Check that the destination is empty or does not exist, and that the selected Compose project has no existing containers. If an installation exists, stop without overwriting files or recreating services.

## 4. Download release files

Download the source archive for the exact tag into a temporary directory. Validate archive paths before extraction and extract only these files:

| Repository file | Purpose |
| --- | --- |
| `compose.yaml` | Service definitions, mounts and networks. |
| `docker/compose.env.example` | Template for generating `.env`. |
| `docker/monito.env` | Monito environment variables. |
| `docker/ggets.env` | Ggets environment variables. |
| `docker/chromium-seccomp.json` | Chromium security profile. |
| `data-examples/monito/settings/config.json` | Runtime configuration template. |
| `data-examples/monito/settings/monito.agente.json` | Monito tool profile template. |
| `data-examples/ggets/config.json` | Ggets configuration template. |

Keep templates in temporary storage until configuration generation is complete. No repository clone, Dockerfiles, source code, Android files or example secrets are needed. Container images are pulled separately in step 6.

## 5. Prepare deployment settings

Generate `.env` beside `compose.yaml` in the installation directory, using `docker/compose.env.example` as the template, with the published registry, version, UID/GID and destination paths. Compose loads this file automatically; do not generate `docker/compose.env` for the installation. Run subsequent Compose commands from the installation directory without `--env-file`. Check proposed subnets against detected host and Docker networks; stop on conflicts without modifying existing networks.

## 6. Pull both images

Pull these two published images using `IMAGE_PREFIX` and `RELEASE_VERSION` from the generated `.env`:

| Image | Contents |
| --- | --- |
| `${IMAGE_PREFIX}monito-box:${RELEASE_VERSION}` | Monito, Skiller and their flows. |
| `${IMAGE_PREFIX}ggets:${RELEASE_VERSION}` | HTTP tools and Telegram support. |

`IMAGE_PREFIX` identifies the published registry namespace and includes the trailing `/`. `RELEASE_VERSION` is the version supplied through `--version`. Pulls and startup must use the same values.

Both images must be available before starting services. Do not pull an Android image or build images on the server; if either pull fails, start neither service.

## 7. Create persistent directories

Create configuration, HOME, workspace, secrets and state directories. Apply permissions for the selected UID/GID; Ggets secrets and private state directories require mode `0700`. Do not copy host credentials or create files containing dummy secrets.

The expected final tree, after generating configuration and starting services, is:

```text
<directory>/
├── compose.yaml
├── .env                            # Version, UID/GID, paths and networking
├── docker/
│   ├── monito.env                  # Monito environment
│   ├── ggets.env                   # Ggets environment
│   └── chromium-seccomp.json
└── data/
    ├── monito/
    │   ├── settings/
    │   │   ├── config.json          # Runtime: resources and webhook server
    │   │   └── monito.agente.json   # Monito tool profile
    │   ├── home/
    │   │   └── .skiller/
    │   │       ├── secrets/         # Empty; user credentials
    │   │       └── db/
    │   │           └── agent.db     # Created by Runtime on startup
    │   └── workspace/
    └── ggets/
        ├── config.json
        ├── secrets/                 # Empty; Telegram not configured
        └── state/                   # Persistent Ggets state
```

Configuration mounts are read-only; HOME, workspace and state are writable. Runtime may create additional internal files under `.skiller/`. No source code, `data-examples/` or temporary downloads remain in the destination; code and flows live in the images.

## 8. Generate configuration

Copy the templates downloaded in step 4 to their deployment paths and substitute only the declared placeholders. Skiller does not perform general environment-variable expansion inside these JSON files.

| Template → output | Substitutions |
| --- | --- |
| `data-examples/monito/settings/config.json` → `data/monito/settings/config.json` | `${MONITO_FLOW_PATH}`, `${MONITO_INTERNAL_IP}` |
| `data-examples/monito/settings/monito.agente.json` → `data/monito/settings/monito.agente.json` | None; copy unchanged. |
| `data-examples/ggets/config.json` → `data/ggets/config.json` | `${GGETS_INTERNAL_IP}`, `${GGETS_TELEGRAM_IP}`, `${GGETS_TELEGRAM_PORT}` |

Read network values from `.env`. Discover `MONITO_FLOW_PATH` from installed-package metadata inside the selected Monito image, using an isolated temporary container with the entrypoint overridden. Verify that the directory contains the Monito and webhook flows; do not hardcode a Python version or `site-packages` path.

The helper loads each JSON template and replaces declared placeholder values before serializing it. Insert IP addresses and paths as strings, and `GGETS_TELEGRAM_PORT` as an integer from 1 to 65535. Fail on missing, unknown or unresolved placeholders; do not evaluate shell expressions. Write validated JSON atomically with the selected ownership.

Leave fixed container paths, API port `8000` and webhook port `8001` unchanged. Do not create provider configuration, credentials or Skiller's global `agent.json`; Skiller manages these during authentication in its persistent HOME.

Success: `OK [configuration]: Generated 3 configuration files.` Failure: `ERROR [configuration]: <file or discovery step>: <reason>`; stop without starting services.

## 9. Validate before startup

Validate JSON, profiles and `docker compose config`. Image inspections use isolated temporary containers without mounting user data or running the normal entrypoint. Resolve any configuration required to start without a provider before considering this workflow implemented.

## 10. Start services and check health

Run `up -d --no-build` and check Ggets and the Skiller server, including reachability from Ggets, within a bounded timeout. Do not create sessions, listeners or register external integrations as health checks. On failure, report the failed step and preserve data for diagnosis; never automatically delete the destination.

## 11. Report the result

Show the destination, version and service status. Explain that provider/model configuration and credentials are still required for conversations. Remove temporary downloads without touching persistent data.

If an interactive terminal is available, ask `Would you like to launch Skiller now to complete authentication? [y/N]`. Only on confirmation, run `docker compose exec monito skiller` from the installation directory, adding `sudo` before `docker` if authorized in step 2. Declining, leaving Skiller without authenticating, or a launch failure does not undo a successful installation; report a launch failure separately.

If the user declines or no interactive terminal is available, show `cd <installation-directory>` followed by the same command so they can launch Skiller later.

## Implementation and acceptance

The executable `install` at the repository root invokes `scripts/install_helper.py`. Run it from a checkout or source archive containing both files. Host dependencies are `/bin/sh`, Python 3.12+, Docker and Compose; sudo is optional when required for Docker access. Python 3.12 is the supported and tested host baseline, not a claim that older interpreters cannot run the helper. No Python packages need installation. `--image-prefix` overrides the published registry namespace; `--health-timeout` sets the health-check deadline in seconds (default: 60).

- A new installation finishes with both services healthy and the structure described above.
- Users do not need to copy examples, discover internal paths or manually duplicate IP addresses.
- A second invocation against the same destination stops without overwriting anything.
- Tests use temporary directories and mocked Docker commands; real testing requires an isolated environment, never the active deployment.
- Installation and upgrades remain separate; this work does not publish or deploy the pending release.
