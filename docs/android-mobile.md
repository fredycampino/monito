# Android with ADB and Appium

The optional `mobile` service combines ADB, Appium 3.9.0 and UiAutomator2 8.7.2.
Monito uses `ADB_SERVER_SOCKET=tcp:mobile:5037` for its existing ADB client and
`APPIUM_URL=http://mobile:4723` for HTTP requests. APPIUM_URL is a convenience
variable, not a new agent tool or automatic session manager.

Only Monito and mobile join the dedicated internal network. Neither port is
published. Ggets has no access. Both APIs grant control of the phone; do not
expose them or enable Appium relaxed security. Monito has no direct USB access.

## Build and configuration

Connect the phone and enable USB debugging. Determine the USB node's numeric
group with `ls -ln /dev/bus/usb/<bus>/<device>`. Its permissions must allow that
group to read/write; host udev rules, if needed, are an administrator task.
Container rules do not configure host permissions.

Set HOST_UID/HOST_GID to the owner of the persistent server HOME, and configure:

```dotenv
ADB_HOME_HOST_DIR=/opt/monito/data/adb/home
ADB_USB_GID=46
```

These are examples, not portable defaults. Prepare the HOME with the selected
ownership before startup. Preserve any existing HOME and `.android/adbkey` and
`adbkey.pub`; never print, replace or delete the keys. The directory variables
retain their ADB names because they describe USB permissions and ADB key storage,
not a separate service. Monito needs no keys.

The USB mount exposes the USB tree, not just one phone. Device rules allow USB
major 189 with wildcard minors for reconnects; host permissions still apply.
Never run another ADB server against the same USB phone, including on the host.

```bash
ADB_USB_GID=46 docker compose -f compose.yaml -f docker/compose.mobile.yaml config --quiet
docker compose -f compose.yaml -f docker/compose.mobile.yaml build mobile monito
```

The image installs Node, Java runtime and Debian ADB, but no full Android SDK,
Build Tools or SDK manager. ANDROID_HOME names the directory installed by the
Debian adb package; it is not a host SDK mount. Appium dependencies come from
appium-lab/package-lock.json via npm ci, never from host node_modules.
Code is read-only; project metadata and extension cache live in /tmp. Only the
ADB HOME persists. Nothing is downloaded at startup, and no phone session is
created automatically. ADB may write authorization keys to HOME at startup.

ADB and Appium are supervised together: if either exits, the container exits
and Compose can restart it. Health checks query both servers without requiring
a connected phone or starting another ADB daemon. Mobile runs without root or
privileged mode, using the configured USB group and device rules.

## Deployment (requires separate authorization)

Do not run `up` on an active deployment without reviewing mounts, sessions and
data. When migrating an existing deployment, stop any old ADB service first and
preserve its HOME. Adding the network and environment recreates Monito and
interrupts its processes. The publication workflow now builds monito-mobile
alongside the base images; this working-tree change has not published an image.
For production, select and pull the same explicit published release for all
three images before recreating any service. Do not build on Max.

```bash
docker compose -f compose.yaml -f docker/compose.mobile.yaml up -d --no-build
docker compose -f compose.yaml -f docker/compose.mobile.yaml exec monito adb devices -l
docker compose -f compose.yaml -f docker/compose.mobile.yaml exec monito \
  curl -fsS http://mobile:4723/status
```

Authorize USB debugging on the phone if prompted. Do not replace existing keys.
To create a session, POST /session with platformName Android, automationName
UiAutomator2, the selected udid, noReset true and autoLaunch false. Read
/session/<id>/source and DELETE /session/<id> when finished. Never run concurrent
sessions against the same phone. Agent command permissions remain independent.

## Verification boundaries

The earlier isolated physical test validated a session and XML read with both
servers in one USB-enabled container, no external network and no Build Tools,
on an already-prepared Samsung. A new-phone bootstrap and session creation using
this production Dockerfile still require authorized physical verification.
CI checks configuration, image build, both servers, driver discovery and shutdown
without USB, user data, external services or active Monito sessions.
