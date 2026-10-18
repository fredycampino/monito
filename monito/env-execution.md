# Execution environment

Before using environment-specific paths, check the current directory and whether
`/.dockerenv` exists using the files tool or a bounded shell command. Do not infer
host access from a path name. If the environment does not match either layout
below, inspect it and ask before assuming repository or workspace paths.

## Development host

Repository target: `~/develop/monito/`.
Skiller source: `~/develop/py/skiller/`, for reference only.
Never create, edit, move or delete files in the Skiller repository.
Repository changes must remain inside the Monito repository.
The development flow selects `agent.dev.json`. Verify paths exist before using
them; use the Monito repository as the shell working directory for repository tasks.

## Monito Box container

Monito is installed at `/opt/monito/monito/` and selects `agent.box.json`.
Installed application files and `/usr/local` are read-only image content.
The host development repositories are not mounted here. Do not translate
`~/develop/monito` into a container path or assume Skiller source is available.

Box starts the CLI and shells in `/data/workspace`. Installed flows, including
`@monito`, resolve through the image's Runtime configuration, independently of cwd.
Use `/data/workspace` as the shell working directory for user work.
Use absolute workspace paths for file tool calls; relative file paths may resolve
from the Runtime startup directory rather than the last shell working directory.

`HOME=/data/home` contains personal state, not the workspace.
`/data/home/.skiller` contains settings, secrets and runtime state; its
`db/agent.db` is the run database. Do not read or display secrets, or manually
modify a live database. Persistent working files belong in `/data/workspace`.
`/tmp` is size-limited temporary storage and is discarded when the container stops.
The host shares only the configured `/data` mount, not its entire filesystem.
