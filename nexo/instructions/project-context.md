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

Remote deployment coordinates (SSH user/host, addresses, domain, admin/data
paths and tunnel configuration) are local operator context, not repository
constants. Obtain them from the user or ignored nexo/local/ notes and verify
them before operations. Inspect actual container names, mounts and configuration;
do not infer them from historical notes. Credentials must never be displayed.
GitHub credentials are not part of the Monito deployment. Publishing images
does not deploy them.

Read contexto/page-oct-20.md only when historical continuity is needed. Its
shared copy omits personal coordinates and session identifiers. Private local
notes, when available, remain historical: neither source proves current state
or authorizes environment changes.
