"""Fresh host installation. No third-party Python dependencies."""

import argparse
import hashlib
import io
import ipaddress
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

FILES = (
    "compose.yaml",
    "docker/compose.env.example",
    "docker/monito.env",
    "docker/ggets.env",
    "docker/chromium-seccomp.json",
    "data-examples/monito/settings/config.json",
    "data-examples/monito/settings/monito.agente.json",
    "data-examples/ggets/config.json",
)
SOURCE = "https://github.com/fredycampino/monito/archive/refs/tags/v{version}.tar.gz"
PREFIX = "ghcr.io/fredycampino/"
VERSION = r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?"
FLOW_DISCOVERY = """import importlib.metadata as m,json
from pathlib import Path
d=m.distribution("monito")
paths=[Path(d.locate_file(f)) for f in d.files if str(f).endswith("packages/monito/monito.yaml")]
assert len(paths)==1
root=paths[0].parent.parent
assert root.is_absolute() and (root/"webhook/webhook.yaml").is_file()
print(json.dumps(str(root)))
"""


class InstallError(Exception):
    pass


def run(args, *, cwd=None, check=True, timeout=120, capture=True, env=None):
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=capture,
        timeout=timeout,
    )
    if check and result.returncode:
        raise InstallError(f"Command failed: {shlex.join(args)}\n{result.stderr or ''}")
    return result


def render(value, values):
    """Typed replacement of whole JSON values, never shell evaluation."""
    if isinstance(value, dict):
        return {k: render(v, values) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, values) for v in value]
    if isinstance(value, str) and "${" in value:
        match = re.fullmatch(r"\$\{([A-Z_]+)\}", value)
        if not match or match[1] not in values:
            raise InstallError(f"Unknown or unresolved placeholder: {value}")
        replacement = values[match[1]]
        if replacement == "" or "${" in str(replacement):
            raise InstallError(f"Missing or unresolved value: {match[1]}")
        return replacement
    return value


def extract_archive(content, destination):
    """Extract an allowlist of regular files only, never links or archive paths."""
    found = set()
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        for member in archive:
            parts = Path(member.name).parts
            if member.name.startswith("/") or ".." in parts:
                raise InstallError("Unsafe archive path")
            relative = "/".join(parts[1:])
            if relative not in FILES:
                continue
            if relative in found or not member.isfile() or member.size > 2_000_000:
                raise InstallError(f"Invalid archive member: {relative}")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
            found.add(relative)
    if found != set(FILES):
        raise InstallError(f"Release missing required files: {sorted(set(FILES) - found)}")


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def env_text(template, values):
    lines = []
    for line in template.splitlines():
        key, separator, _ = line.partition("=")
        if separator and key in values:
            # Single quoting prevents Compose interpolation of host paths.
            value = str(values[key])
            if any(c in value for c in "\n\r'\\"):
                raise InstallError(f"Unsupported character in environment value: {key}")
            line = f"{key}='{value}'"
        lines.append(line)
    return "\n".join(lines) + "\n"


class Installer:
    def __init__(self, args):
        self.args = args
        self.destination = Path(args.dir).expanduser().resolve()
        self.project = "monito-" + hashlib.sha256(str(self.destination).encode()).hexdigest()[:12]
        self.docker = ["docker"]
        self.values = {}

    def compose(self, *args, **kwargs):
        return run(
            [*self.docker, "compose", "--project-name", self.project, *args],
            cwd=self.destination,
            env={
                **{k: v for k, v in os.environ.items() if not k.startswith("COMPOSE_")},
                **{k: str(v) for k, v in self.values.items()},
                "COMPOSE_PROJECT_NAME": self.project,
            },
            **kwargs,
        )

    def prerequisites(self):
        errors = []

        def check(name, condition, message):
            if condition:
                print(f"OK [{name}]: available")
            else:
                errors.append(f"ERROR [{name}]: {message}")

        check("platform", platform.system() == "Linux", "Linux is required.")
        check("python", sys.version_info >= (3, 12), "Python 3.12+ is required.")
        check("docker-cli", shutil.which("docker"), "Docker CLI was not found.")
        parent = self.destination
        while not parent.exists():
            parent = parent.parent
        check(
            "destination",
            parent.is_dir() and os.access(parent, os.W_OK | os.X_OK),
            f"Cannot create files under {parent}.",
        )
        try:
            with tempfile.TemporaryDirectory() as temporary:
                Path(temporary, "probe").write_text("probe")
            print("OK [temporary-directory]: writable")
        except OSError:
            errors.append("ERROR [temporary-directory]: Cannot create temporary files.")
        if shutil.which("docker"):
            try:
                # Docker gives DOCKER_CONTEXT precedence over DOCKER_HOST.
                context_name = os.environ.get("DOCKER_CONTEXT")
                endpoint = os.environ.get("DOCKER_HOST")
                if context_name or not endpoint:
                    command = ["docker", "context", "inspect"]
                    if context_name:
                        command.append(context_name)
                    context = run(command)
                    endpoint = json.loads(context.stdout)[0]["Endpoints"]["docker"]["Host"]
                if not endpoint.startswith("unix://"):
                    raise InstallError("Only a local Unix Docker socket is supported.")
                self.docker = ["docker", "--host", endpoint]
                info = run([*self.docker, "info", "--format", "{{.OSType}}"], check=False)
                if info.returncode and "permission denied" in info.stderr.lower():
                    prompt = (
                        "Docker requires elevated permissions. "
                        "Authorize sudo for Docker commands only? [y/N] "
                    )
                    if (
                        not sys.stdin.isatty()
                        or not shutil.which("sudo")
                        or input(prompt).strip().lower() not in ("y", "yes")
                    ):
                        raise InstallError(
                            "Docker access requires sudo authorization; rerun interactively."
                        )
                    run(["sudo", "-v"], capture=False)
                    self.docker = ["sudo", "docker", "--host", endpoint]
                    info = run([*self.docker, "info", "--format", "{{.OSType}}"], check=False)
                check(
                    "docker-engine",
                    info.returncode == 0 and info.stdout.strip() == "linux",
                    "A local Linux Docker Engine must be accessible.",
                )
                compose = run([*self.docker, "compose", "version", "--short"], check=False)
                version = re.match(r"v?(\d+)\.(\d+)\.(\d+)", compose.stdout.strip())
                check(
                    "compose",
                    version and tuple(map(int, version.groups())) >= (2, 33, 1),
                    "Docker Compose plugin 2.33.1+ is required.",
                )
            except (ValueError, KeyError, IndexError, InstallError) as exc:
                errors.append(f"ERROR [docker-engine]: {exc}")
        if errors:
            raise InstallError("\n".join(errors) + "\nPrerequisites failed; installation stopped.")
        print("Prerequisites passed.")

    def confirm_new(self):
        if self.destination.exists() and (
            not self.destination.is_dir() or any(self.destination.iterdir())
        ):
            raise InstallError(
                f"Destination is not empty: {self.destination}. No files were changed."
            )
        containers = run(
            [
                *self.docker,
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
            ]
        ).stdout.strip()
        if containers:
            raise InstallError(f"Compose project already exists: {self.project}")

    def settings(self, source):
        values = dict(
            re.findall(
                r"^([A-Z_]+)=(.*)$", (source / "docker/compose.env.example").read_text(), re.M
            )
        )
        values.update(
            IMAGE_PREFIX=self.args.image_prefix,
            RELEASE_VERSION=self.args.version,
            HOST_UID=os.getuid(),
            HOST_GID=os.getgid(),
        )
        values["COMPOSE_PROJECT_NAME"] = self.project
        networks = []
        ids = run([*self.docker, "network", "ls", "-q"]).stdout.split()
        if ids:
            networks = json.loads(run([*self.docker, "network", "inspect", *ids]).stdout)
        occupied = [
            ipaddress.ip_network(c["Subnet"], strict=False)
            for n in networks
            for c in n.get("IPAM", {}).get("Config", [])
            if c.get("Subnet")
        ]
        # Linux routing table includes connected interfaces and VPN routes. Ignore default routes.
        for line in Path("/proc/net/route").read_text().splitlines()[1:]:
            fields = line.split()
            if fields[1] != "00000000":
                address = int(fields[1], 16).to_bytes(4, "little")
                mask = int(fields[7], 16).to_bytes(4, "little")
                occupied.append(
                    ipaddress.ip_network(
                        f"{ipaddress.IPv4Address(address)}/{ipaddress.IPv4Address(mask)}",
                        strict=False,
                    )
                )
        for name in ("INTERNAL_SUBNET", "INGRESS_SUBNET"):
            subnet = ipaddress.ip_network(values[name])
            if any(n.version == subnet.version and n.overlaps(subnet) for n in occupied):
                raise InstallError(f"Network conflict: {name}={subnet}; no networks were changed.")
        self.values = values

    def generate(self, source, flow_path):
        dest = self.destination
        dest.mkdir(parents=True, exist_ok=True)
        for name in (
            "compose.yaml",
            "docker/monito.env",
            "docker/ggets.env",
            "docker/chromium-seccomp.json",
        ):
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
        for directory in (
            "monito/home",
            "monito/workspace",
            "monito/settings",
            "ggets/secrets",
            "ggets/state",
        ):
            (dest / "data" / directory).mkdir(parents=True, exist_ok=True, mode=0o700)
        template = (source / "docker/compose.env.example").read_text()
        atomic_write(
            dest / ".env",
            env_text(template, self.values) + f"COMPOSE_PROJECT_NAME={self.project}\n",
        )
        replacements = {
            k: self.values[k]
            for k in ("MONITO_INTERNAL_IP", "GGETS_INTERNAL_IP", "GGETS_TELEGRAM_IP")
        }
        replacements.update(
            MONITO_FLOW_PATH=flow_path, GGETS_TELEGRAM_PORT=int(self.values["GGETS_TELEGRAM_PORT"])
        )
        if not 1 <= replacements["GGETS_TELEGRAM_PORT"] <= 65535:
            raise InstallError("Invalid Telegram receiver port")
        for name in (
            "monito/settings/config.json",
            "monito/settings/monito.agente.json",
            "ggets/config.json",
        ):
            payload = json.loads((source / "data-examples" / name).read_text())
            atomic_write(
                dest / "data" / name, json.dumps(render(payload, replacements), indent=2) + "\n"
            )
        print("OK [configuration]: Generated 3 configuration files.")

    def health(self):
        code = """import json,urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
r=urllib.request.Request("http://%s:8000/health/check",data=b"{}",headers={"Content-Type":"application/json"})
assert json.load(opener.open(r,timeout=3))["status"]=="ok"
assert opener.open("http://%s:8001/health",timeout=3).status==200
""" % (self.values["GGETS_INTERNAL_IP"], self.values["MONITO_INTERNAL_IP"])
        deadline = time.monotonic() + self.args.health_timeout
        while time.monotonic() < deadline:
            result = self.compose(
                "exec", "-T", "ggets", "python", "-c", code, check=False, timeout=15
            )
            if result.returncode == 0:
                raw = self.compose("ps", "--format", "json").stdout.strip()
                states = (
                    json.loads(raw)
                    if raw.startswith("[")
                    else [json.loads(line) for line in raw.splitlines() if line.strip()]
                )
                if {s["Service"] for s in states if s["State"] == "running"} >= {"monito", "ggets"}:
                    return
            time.sleep(2)
        raise InstallError(
            "Health checks timed out. Data and containers were preserved for diagnosis."
        )

    def execute(self):
        self.prerequisites()
        self.confirm_new()
        with tempfile.TemporaryDirectory(prefix="monito-install-") as temporary:
            source = Path(temporary)
            with urllib.request.urlopen(
                SOURCE.format(version=self.args.version), timeout=60
            ) as response:
                archive = response.read(64_000_001)
            if len(archive) > 64_000_000:
                raise InstallError("Release archive exceeds 64 MB")
            extract_archive(archive, source)
            self.settings(source)
            for image in ("monito-box", "ggets"):
                run(
                    [*self.docker, "pull", f"{self.args.image_prefix}{image}:{self.args.version}"],
                    capture=False,
                    timeout=600,
                )
            discovery = run(
                [
                    *self.docker,
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--read-only",
                    "--entrypoint",
                    "python",
                    f"{self.args.image_prefix}monito-box:{self.args.version}",
                    "-c",
                    FLOW_DISCOVERY,
                ]
            )
            flow_path = json.loads(discovery.stdout)
            if not isinstance(flow_path, str) or not flow_path.startswith("/"):
                raise InstallError("Invalid flow resource path")
            self.generate(source, flow_path)
            self.compose("config", "--quiet")
            self.compose("up", "-d", "--no-build", capture=False, timeout=180)
            self.health()
        print(
            f"\nMonito installation completed successfully.\nVersion: {self.args.version}"
            f"\nDirectory: {self.destination}\nMonito: running\nSkiller: healthy\nGgets: healthy"
        )
        command = [*self.docker, "compose", "exec", "monito", "skiller"]
        if sys.stdin.isatty() and input(
            "Would you like to launch Skiller now to complete authentication? [y/N] "
        ).strip().lower() in ("y", "yes"):
            result = run(command, cwd=self.destination, capture=False, check=False, timeout=None)
            if result.returncode:
                print("Skiller launch failed; installation remains complete.")
        else:
            print(
                f"To authenticate later:\n  cd {shlex.quote(str(self.destination))}"
                f"\n  {shlex.join(command)}"
            )


def main():
    parser = argparse.ArgumentParser(prog="./install", description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dir", required=True)
    parser.add_argument("--image-prefix", default=PREFIX)
    parser.add_argument("--health-timeout", type=int, default=60)
    args = parser.parse_args()
    if not re.fullmatch(VERSION, args.version):
        parser.error("--version must be an explicit release version without v")
    if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*/", args.image_prefix):
        parser.error("--image-prefix must be a registry namespace ending in /")
    if args.health_timeout < 1:
        parser.error("--health-timeout must be positive")
    try:
        Installer(args).execute()
    except (InstallError, OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print(f"ERROR [installation]: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Installation interrupted; existing data was preserved.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
