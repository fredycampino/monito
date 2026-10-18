# Versioned deployment

Use the root `compose.yaml` for both local builds and published images.
Both services share `IMAGE_PREFIX` and `RELEASE_VERSION`. The
release must have completed publication of both images. No server-side build,
automatic deployment, or PyPI installation is required.

## Prepare

Use a distribution of the selected release's deployment files: `compose.yaml`,
`docker/*.env`, `docker/compose.env.example`, and the `data-examples/` data tree. Obtain these from the tagged
source archive; a repository clone is not required. Keep them under a deployment
root such as `/srv/monito`. Run the commands below from that root.

Copy `docker/compose.env.example` to `docker/compose.env` on first setup. Set
`IMAGE_PREFIX=ghcr.io/fredycampino/` and `RELEASE_VERSION` to the selected
published tag without the leading `v`, set
UID/GID and host paths, and review subnets. Do not use `latest` or `dev`.
This selection is not changed automatically by release preparation.

Prepare persistent directories and copy the configuration examples as described
in [Local deployment](local-deployment.md#1-prepare). Do not overwrite
existing settings or secrets. Keep JSON listen addresses aligned with Compose
IPs and ports. Provision LLM configuration and Telegram secrets separately.

Relative bind mounts and `env_file` paths resolve from the directory containing
`compose.yaml`, not from the env file directory. Keep the project name stable
across upgrades; use a separate project and non-overlapping networks if running
alongside a development deployment.

## Validate, pull and start

```bash
docker compose -p monito --env-file docker/compose.env config --quiet
docker compose -p monito --env-file docker/compose.env pull &&
docker compose -p monito --env-file docker/compose.env up -d --no-build
```

The Compose build definitions are retained for local development; deployment
uses `pull` and `up --no-build`, never `build`. Empty `IMAGE_PREFIX` and
`RELEASE_VERSION=dev` are local defaults, not a production selection.

Pull both images successfully before recreating either service. Close interactive
sessions before upgrades. There is no atomic two-container upgrade; schedule a
maintenance window. Do not delete persistent data or volumes.

## Verify

```bash
docker compose -p monito --env-file docker/compose.env ps
docker compose -p monito --env-file docker/compose.env logs --tail=50
docker compose -p monito --env-file docker/compose.env exec ggets ggets health check
docker compose -p monito --env-file docker/compose.env exec monito skiller @monito
```

Check persistence, flow resolution and required integrations as well as container
status. Monito starts idle: start/check its Skiller server and listeners explicitly
when webhooks are needed. Do not register external integrations as a health check.

## Rollback

Select the previous known-good `RELEASE_VERSION` in `docker/compose.env` and repeat
validate, pull, start and verify for both services. Preserve environment-specific
paths and secrets. Back up state before upgrades; an incompatible state migration
may require a documented recovery rather than simply selecting older images.
