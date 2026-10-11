import json
from pathlib import Path

from sk_cloudflared.tunnel import TunnelService


class LoggedIn:
    class Status:
        authenticated = True

    def status(self) -> Status:
        return self.Status()


def service(tmp_path: Path) -> TunnelService:
    return TunnelService(state_root=tmp_path / "monito" / "cloudflared", login=LoggedIn())


def config(tmp_path: Path) -> Path:
    path = tmp_path / "skiller-webhooks.yml"
    path.write_text("sensitive configuration is not read by Monito\n", encoding="utf-8")
    return path


def test_register_records_path_without_reading_configuration(monkeypatch, tmp_path: Path) -> None:
    tunnel = service(tmp_path)
    yaml = config(tmp_path)
    read_calls: list[Path] = []
    original_read_text = Path.read_text

    def read_text(path: Path, *args, **kwargs):
        if path == yaml:
            read_calls.append(path)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)

    result = tunnel.register("skiller", str(yaml))

    assert result.ok
    assert result.config_path == str(yaml)
    assert read_calls == []
    assert tunnel._load("skiller").config_path == str(yaml)


def test_register_refuses_to_replace_another_config_path(tmp_path: Path) -> None:
    tunnel = service(tmp_path)
    first = config(tmp_path)
    second = tmp_path / "other.yml"
    second.write_text("another secret", encoding="utf-8")
    tunnel.register("skiller", str(first))

    result = tunnel.register("skiller", str(second))

    assert not result.ok
    assert tunnel._load("skiller").config_path == str(first)


def test_open_runs_exact_user_provided_config_path(monkeypatch, tmp_path: Path) -> None:
    tunnel = service(tmp_path)
    yaml = config(tmp_path)
    tunnel.register("skiller", str(yaml))
    monkeypatch.setattr(tunnel, "_executable", lambda: "/bin/cloudflared")
    commands: list[list[str]] = []

    class Process:
        pid = 42

        def poll(self):
            return None

    def launch(command, **kwargs):
        commands.append(command)
        return Process()

    monkeypatch.setattr("sk_cloudflared.tunnel.subprocess.Popen", launch)

    result = tunnel.open("skiller")

    assert result.ok
    assert commands == [["/bin/cloudflared", "tunnel", "--config", str(yaml), "run"]]


def test_close_only_stops_the_selected_verified_connector(monkeypatch, tmp_path: Path) -> None:
    tunnel = service(tmp_path)
    first = config(tmp_path)
    second = tmp_path / "other.yml"
    second.write_text("other", encoding="utf-8")
    tunnel.register("skiller", str(first))
    tunnel.register("other", str(second))
    first_state = tunnel._load("skiller")
    second_state = tunnel._load("other")
    tunnel._save(type(first_state)(first_state.name, first_state.config_path, 42))
    tunnel._save(type(second_state)(second_state.name, second_state.config_path, 43))
    monkeypatch.setattr(tunnel, "_managed_pid", lambda state: 42 if state.name == "skiller" else 43)
    monkeypatch.setattr(tunnel, "_wait_stopped", lambda pid: True)
    killed: list[int] = []
    monkeypatch.setattr("sk_cloudflared.tunnel.os.kill", lambda pid, signal: killed.append(pid))

    result = tunnel.close("skiller")

    assert result.ok
    assert killed == [42]
    assert tunnel._load("skiller").pid is None
    assert tunnel._load("other").pid == 43


def test_list_returns_remote_tunnels_without_local_config_access(
    monkeypatch, tmp_path: Path
) -> None:
    tunnel = service(tmp_path)
    monkeypatch.setattr(tunnel, "_executable", lambda: "/bin/cloudflared")

    class Result:
        returncode = 0
        stdout = json.dumps([{"id": "remote-id", "name": "skiller", "connections": []}])

    monkeypatch.setattr("sk_cloudflared.tunnel.subprocess.run", lambda *args, **kwargs: Result())

    result = tunnel.list()

    assert result.ok
    assert result.tunnels == [{"id": "remote-id", "name": "skiller", "connections": []}]
