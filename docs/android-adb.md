# Android over USB with ADB

## Architecture

Monito runs the ADB client. An optional `adb` service runs the ADB server and
accesses USB on the Linux host. The host does not need ADB installed.
The client uses `ADB_SERVER_SOCKET=tcp:adb:5037` over a dedicated internal Docker
network. No ADB port is published. Both images inherit the same ADB installation
from the `adb-base` stage in `docker/Dockerfile.monito` (Debian package).

The server uses HOME=/data/home. Its `.android/adbkey` and `adbkey.pub` persist
in the host directory selected by `ADB_HOME_HOST_DIR`; Monito needs neither key.
Do not print private keys or replace existing Android authorization state.

## Host preparation

Connect the dedicated phone, enable USB debugging and verify it appears in
`lsusb`. Determine the access group with `ls -l /dev/bus/usb/<bus>/<device>` and
its numeric GID with `getent group <group>`.

Create an empty server HOME owned by the Compose HOST_UID/HOST_GID. For example,
on Max the proposed directory is `/opt/monito/data/adb/home`. Set these values in
the deployment environment (the GID below was observed on Max, not portable):

```dotenv
ADB_HOME_HOST_DIR=/opt/monito/data/adb/home
ADB_USB_GID=46
```

The phone's USB node must grant this group read/write access. On Max the Samsung
node was already owned by `root:plugdev` with mode 0664. If permissions differ,
an administrator must prepare a persistent udev rule for the intended phone,
then reconnect and verify the permissions. Installing udev rules inside the ADB
container does not configure the host.

The override mounts `/dev/bus/usb` and allows read/write for USB character-device
major 189 with wildcard minors, allowing reconnections without editing Compose.
This exposes the USB tree to the ADB service, not exclusively one phone; host
permissions still apply. Monito receives no direct USB mount. Neither service
requires privileged mode. The ADB server is unauthenticated to its network clients;
do not attach other services to this dedicated network or publish port 5037.

## Build and run

Use the base deployment guide for configuration and persistent data. Enable ADB
explicitly with both files, from the repository root:

```bash
docker compose -f compose.yaml -f docker/compose.adb.yaml config
docker compose -f compose.yaml -f docker/compose.adb.yaml build monito adb
```

For a published deployment, select the explicit release version and pull the
optional `monito-adb` image in addition to the two base images before recreating
anything. Do not build on Max. Back up the existing deployment and preserve all
HOME, workspace, DB and configuration mounts. Enabling the override recreates
Monito to add its environment variable and network; this interrupts processes.
Deployment requires explicit authorization.

```bash
docker compose -f compose.yaml -f docker/compose.adb.yaml up -d --no-build
docker compose -f compose.yaml -f docker/compose.adb.yaml exec monito /usr/bin/adb devices -l
```

Unlock the phone and accept its USB debugging authorization prompt, optionally
remembering the server. `unauthorized` requires approval on the phone; an empty
list requires checking USB enumeration, permissions and container logs.

Use `/usr/bin/adb` while verifying: an older workspace `bin/adb` wrapper may
shadow the installed client and use a different version. Do not delete existing
workspace tools automatically. Check PATH resolution before switching everyday use.

## Acceptance verification

With authorization for the dedicated phone:

- Confirm `/usr/bin/adb devices -l` from Monito shows it as `device`.
- Use `adb -s <serial> shell getprop ro.product.model` for a read-only model query.
- Reconnect the phone and verify detection without editing Compose.
- Recreate only the ADB service, preserving its HOME, and verify authorization
  remains valid.
- Verify port 5037 is not published and Ggets is not attached to the ADB network.

These physical-device checks are not covered by structural tests or a successful
image build. Never claim them passed without executing them against the phone.
