"""Installer tests never contact Docker, registries or user data."""

import importlib.util
import io
import json
import subprocess
import tarfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("install_helper", ROOT / "scripts/install_helper.py")
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def make_installer(tmp_path):
    return installer.Installer(
        SimpleNamespace(
            dir=str(tmp_path / "deployment"),
            version="0.1.0-beta.11",
            image_prefix="registry.example/team/",
            health_timeout=1,
        )
    )


def archive_bytes(extra=None):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name in installer.FILES:
            content = (ROOT / name).read_bytes()
            info = tarfile.TarInfo("release/" + name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        if extra:
            archive.addfile(extra)
    return output.getvalue()


def test_templates_render_with_types():
    data = {"path": "${PATH}", "port": "${PORT}", "other": [True, "/fixed"]}
    assert installer.render(data, {"PATH": "/a path", "PORT": 8001}) == {
        "path": "/a path",
        "port": 8001,
        "other": [True, "/fixed"],
    }
    for value in ("${MISSING}", "prefix${PORT}"):
        with pytest.raises(installer.InstallError):
            installer.render(value, {"PORT": 8001})


def test_archive_allowlist_and_traversal(tmp_path):
    installer.extract_archive(archive_bytes(), tmp_path)
    assert (tmp_path / "compose.yaml").exists()
    assert not (tmp_path / "data-examples/ggets/secrets").exists()
    with pytest.raises(installer.InstallError, match="Unsafe"):
        installer.extract_archive(archive_bytes(tarfile.TarInfo("../escape")), tmp_path)


def test_archive_rejects_missing_files(tmp_path):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz"):
        pass
    with pytest.raises(installer.InstallError, match="missing"):
        installer.extract_archive(output.getvalue(), tmp_path)


def test_existing_destination_never_calls_docker(tmp_path, monkeypatch):
    instance = make_installer(tmp_path)
    instance.destination.mkdir()
    marker = instance.destination / "keep"
    marker.write_text("user data")
    command = Mock()
    monkeypatch.setattr(installer, "run", command)
    with pytest.raises(installer.InstallError, match="not empty"):
        instance.confirm_new()
    assert marker.read_text() == "user data"
    command.assert_not_called()


def test_generate_preserves_skiller_initialization(tmp_path):
    instance = make_installer(tmp_path)
    instance.values = dict(
        MONITO_INTERNAL_IP="172.28.0.3",
        GGETS_INTERNAL_IP="172.28.0.2",
        GGETS_TELEGRAM_IP="172.29.0.2",
        GGETS_TELEGRAM_PORT="8001",
        IMAGE_PREFIX="registry.example/team/",
        RELEASE_VERSION="0.1.0-beta.11",
        HOST_UID="1000",
        HOST_GID="1000",
    )
    instance.generate(ROOT, "/installed/packages")
    dest = instance.destination
    assert not (dest / "data/monito/home/.skiller").exists()
    assert not (dest / "docker/compose.env").exists()
    assert "RELEASE_VERSION='0.1.0-beta.11'" in (dest / ".env").read_text()
    runtime = json.loads((dest / "data/monito/settings/config.json").read_text())
    assert runtime["flow_paths"] == ["/installed/packages"]
    config = json.loads((dest / "data/ggets/config.json").read_text())
    assert config["telegram"]["receiver_port"] == 8001
    assert (dest / "data/ggets/secrets").stat().st_mode & 0o777 == 0o700
    assert list((dest / "data/ggets/secrets").iterdir()) == []


def test_pull_failure_never_writes_or_starts(tmp_path, monkeypatch):
    instance = make_installer(tmp_path)
    monkeypatch.setattr(instance, "prerequisites", lambda: None)
    monkeypatch.setattr(instance, "confirm_new", lambda: None)
    monkeypatch.setattr(instance, "settings", lambda source: None)
    response = io.BytesIO(archive_bytes())
    monkeypatch.setattr(installer.urllib.request, "urlopen", lambda *a, **k: response)
    command = Mock(side_effect=installer.InstallError("pull failed"))
    monkeypatch.setattr(installer, "run", command)
    with pytest.raises(installer.InstallError, match="pull failed"):
        instance.execute()
    assert not instance.destination.exists()
    assert command.call_count == 1
    assert "pull" in command.call_args.args[0]


def test_full_install_with_mocked_docker(tmp_path, monkeypatch):
    instance = make_installer(tmp_path)
    monkeypatch.setattr(instance, "prerequisites", lambda: None)
    monkeypatch.setattr(
        instance,
        "settings",
        lambda source: setattr(
            instance,
            "values",
            dict(
                MONITO_INTERNAL_IP="172.28.0.3",
                GGETS_INTERNAL_IP="172.28.0.2",
                GGETS_TELEGRAM_IP="172.29.0.2",
                GGETS_TELEGRAM_PORT="8001",
            ),
        ),
    )
    monkeypatch.setattr(
        installer.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(archive_bytes())
    )
    monkeypatch.setattr(installer.sys.stdin, "isatty", lambda: False)
    commands = []

    def command(args, **kwargs):
        commands.append(args)
        output = ""
        if "run" in args:
            output = json.dumps("/installed/packages")
        elif "ps" in args and "--format" in args:
            output = "\n".join(
                json.dumps({"Service": s, "State": "running"}) for s in ("monito", "ggets")
            )
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(installer, "run", command)
    instance.execute()
    pulls = [i for i, cmd in enumerate(commands) if "pull" in cmd]
    start = next(i for i, cmd in enumerate(commands) if "up" in cmd)
    assert len(pulls) == 2 and max(pulls) < start
    assert "--no-build" in commands[start]
    assert not any("--env-file" in cmd for cmd in commands)
    assert (instance.destination / ".env").exists()


def test_health_timeout_preserves_data(tmp_path, monkeypatch):
    instance = make_installer(tmp_path)
    instance.values = {"GGETS_INTERNAL_IP": "172.28.0.2", "MONITO_INTERNAL_IP": "172.28.0.3"}
    monkeypatch.setattr(
        instance, "compose", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "not ready")
    )
    clock = iter((0, 0, 2))
    monkeypatch.setattr(installer.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(installer.time, "sleep", lambda seconds: None)
    with pytest.raises(installer.InstallError, match="preserved"):
        instance.health()


@pytest.mark.parametrize("approve", [True, False])
def test_docker_permissions_require_explicit_authorization(tmp_path, monkeypatch, approve):
    instance = make_installer(tmp_path)
    monkeypatch.setattr(installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/bin/" + name)
    monkeypatch.setattr(installer.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y" if approve else "n")
    commands = []

    def command(args, **kwargs):
        commands.append(args)
        output, error, status = "", "", 0
        if "context" in args:
            output = json.dumps([{"Endpoints": {"docker": {"Host": "unix:///test/docker.sock"}}}])
        elif "info" in args:
            if args[0] == "sudo":
                output = "linux\n"
            else:
                error, status = "permission denied", 1
        elif "version" in args:
            output = "2.33.1"
        return subprocess.CompletedProcess(args, status, output, error)

    monkeypatch.setattr(installer, "run", command)
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.delenv("DOCKER_CONTEXT", raising=False)
    if approve:
        instance.prerequisites()
        assert instance.docker == ["sudo", "docker", "--host", "unix:///test/docker.sock"]
        assert ["sudo", "-v"] in commands
    else:
        with pytest.raises(installer.InstallError, match="authorization"):
            instance.prerequisites()
        assert not any(cmd[0] == "sudo" for cmd in commands)


def test_network_conflict_stops_before_destination_creation(tmp_path, monkeypatch):
    instance = make_installer(tmp_path)

    def command(args, **kwargs):
        output = "network-id"
        if "inspect" in args:
            output = json.dumps([{"IPAM": {"Config": [{"Subnet": "172.28.0.0/16"}]}}])
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(installer, "run", command)
    with pytest.raises(installer.InstallError, match="Network conflict"):
        instance.settings(ROOT)
    assert not instance.destination.exists()


def test_environment_quotes_paths_without_interpolation():
    text = installer.env_text("PATH=old\n", {"PATH": "/a path/$literal"})
    assert text == "PATH='/a path/$literal'\n"
    with pytest.raises(installer.InstallError, match="Unsupported character"):
        installer.env_text("PATH=old\n", {"PATH": "/bad\npath"})


@pytest.mark.parametrize(
    "context_name,host,endpoint",
    [
        ("selected", "unix:///ignored.sock", "unix:///context.sock"),
        (None, "unix:///explicit.sock", "unix:///explicit.sock"),
        (None, None, "unix:///context.sock"),
        ("remote", "unix:///local.sock", "ssh://remote"),
    ],
)
@pytest.mark.parametrize("sudo", [False, True])
def test_effective_docker_endpoint(tmp_path, monkeypatch, context_name, host, endpoint, sudo):
    instance = make_installer(tmp_path)
    monkeypatch.setattr(installer.platform, "system", lambda: "Linux")
    monkeypatch.setattr(installer.sys, "version_info", (3, 12))
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/bin/" + name)
    monkeypatch.setattr(installer.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    for name, value in (("DOCKER_CONTEXT", context_name), ("DOCKER_HOST", host)):
        monkeypatch.delenv(name, raising=False)
        if value:
            monkeypatch.setenv(name, value)
    commands = []

    def command(args, **kwargs):
        commands.append(args)
        output = ""
        if "context" in args:
            assert args == ["docker", "context", "inspect"] + (
                [context_name] if context_name else []
            )
            output = json.dumps([{"Endpoints": {"docker": {"Host": endpoint}}}])
        elif "info" in args:
            if sudo and args[0] != "sudo":
                return subprocess.CompletedProcess(args, 1, "", "permission denied")
            output = "linux"
        elif "version" in args:
            output = "2.33.1"
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(installer, "run", command)
    if endpoint.startswith("ssh:"):
        with pytest.raises(installer.InstallError, match="local Unix"):
            instance.prerequisites()
        assert not any("info" in cmd or cmd[0] == "sudo" for cmd in commands)
        return
    instance.prerequisites()
    assert instance.docker == (["sudo"] if sudo else []) + ["docker", "--host", endpoint]
    instance.confirm_new()
    instance.compose("config", "--quiet")
    for cmd in commands:
        if any(action in cmd for action in ("info", "compose", "ps")):
            assert cmd[cmd.index("--host") + 1] == endpoint
    if host and not context_name:
        assert not any("context" in cmd for cmd in commands)
