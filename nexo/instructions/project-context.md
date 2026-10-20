# Project map

Monito is the Box agent, packaged in packages/monito. Ggets (packages/tools)
provides HTTP/CLI tools, Health and Telegram. packages/webhook contains the
listener flow. Read the current implementations rather than assuming historical
paths, versions or run IDs are current.

Authoritative project references:
- docs/workflows.md: feature, release, publish and deploy procedures.
- docs/deployment.md, docs/local-deployment.md, docs/docker-spec.md: deployment.
- compose.yaml and docker/: images, networking and lifecycle.
- data-examples/: expected configuration and persistent-data structure.
- CHANGELOG.md and VERSION: current delivery state.
- docs/todo/: local pending work, currently ignored by Git.

Box uses /data/workspace and HOME=/data/home; its installed code is read-only.
Runtime and agent profiles mount at /etc/monito/config.json and agent.json.
The host development repositories are not mounted in Box. Never infer host
access from a container path. Shell permissions and command allowlists differ.

Telegram: public tunnel -> Ggets -> internal Skiller server -> webhook listener
-> subscriber run. Delivery must use the subscriber's workspace, not the
installed listener directory. Persistent WAITING state does not prove the HTTP
server is running. Check health and actual delivery independently.

Max deployment (historical coordinates; verify before operations): SSH user max,
host max-server.local, Wi-Fi 192.168.1.202, previous wired IP 192.168.1.199.
Admin directory ~/server-admin/monito; persistent data /opt/monito/data.
Containers monito-monito-1 and monito-ggets-1. Public URL monito.campino.me;
Cloudflared config /home/max/.cloudflared/monito.yaml, managed by systemd.
Credentials must never be displayed. GitHub credentials are not part of the
Monito deployment. Publishing images does not deploy them.

Read contexto/page-oct-20.md only when historical continuity is needed. It is a
snapshot, not proof of current state or authorization to change environments.
