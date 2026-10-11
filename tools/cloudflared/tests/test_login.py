from pathlib import Path

from sk_cloudflared.login import LoginService
from sk_cloudflared.state import LoginState, load_login_state, save_login_state


def service(tmp_path: Path) -> LoginService:
    return LoginService(
        state_root=tmp_path / "monito" / "cloudflared", cert_root=tmp_path / "cloudflared"
    )


def test_start_reports_missing_binary_without_creating_state(monkeypatch, tmp_path: Path) -> None:
    login = service(tmp_path)
    monkeypatch.setattr(login, "_executable", lambda: None)

    result = login.start()

    assert result.status == "error"
    assert result.running is False
    assert load_login_state(tmp_path / "monito" / "cloudflared") is None


def test_start_launches_human_login_and_records_only_pid(monkeypatch, tmp_path: Path) -> None:
    login = service(tmp_path)
    captured: list[object] = []
    monkeypatch.setattr(login, "_executable", lambda: "/bin/cloudflared")
    monkeypatch.setattr(login, "_authenticated", lambda executable: False)

    class Process:
        pid = 42

        def poll(self):
            return None

    def launch(command, **kwargs):
        captured.extend([command, kwargs])
        return Process()

    monkeypatch.setattr("sk_cloudflared.login.subprocess.Popen", launch)

    result = login.start()

    assert result.status == "ok"
    assert result.running is True
    assert result.pid == 42
    assert captured[0] == ["/bin/cloudflared", "tunnel", "login"]
    assert load_login_state(tmp_path / "monito" / "cloudflared") == LoginState(pid=42)
    assert "Complete Cloudflare authorization" in result.message


def test_start_is_idempotent_while_monito_login_is_running(monkeypatch, tmp_path: Path) -> None:
    login = service(tmp_path)
    save_login_state(tmp_path / "monito" / "cloudflared", LoginState(pid=42))
    monkeypatch.setattr(login, "_executable", lambda: "/bin/cloudflared")
    monkeypatch.setattr(login, "_authenticated", lambda executable: False)
    monkeypatch.setattr(login, "_is_login_process", lambda pid: pid == 42)
    monkeypatch.setattr("sk_cloudflared.login.subprocess.Popen", lambda *args, **kwargs: None)

    result = login.start()

    assert result.status == "ok"
    assert result.running is True
    assert result.pid == 42


def test_status_marks_certificate_as_authenticated(monkeypatch, tmp_path: Path) -> None:
    login = service(tmp_path)
    cert_path = tmp_path / "cloudflared" / "cert.pem"
    cert_path.parent.mkdir(parents=True)
    cert_path.write_text("not-a-real-secret")
    monkeypatch.setattr(login, "_executable", lambda: "/bin/cloudflared")

    result = login.status()

    assert result.status == "ok"
    assert result.authenticated is True
    assert result.running is False


def test_status_removes_stale_state_without_touching_credentials(
    monkeypatch, tmp_path: Path
) -> None:
    login = service(tmp_path)
    state_root = tmp_path / "monito" / "cloudflared"
    save_login_state(state_root, LoginState(pid=999))
    monkeypatch.setattr(login, "_executable", lambda: "/bin/cloudflared")
    monkeypatch.setattr(login, "_authenticated", lambda executable: False)
    monkeypatch.setattr(login, "_is_login_process", lambda pid: False)

    result = login.status()

    assert result.running is False
    assert load_login_state(state_root) is None
    assert not (tmp_path / "cloudflared" / "cert.pem").exists()


def test_stop_does_not_signal_process_not_owned_by_monito(monkeypatch, tmp_path: Path) -> None:
    login = service(tmp_path)
    state_root = tmp_path / "monito" / "cloudflared"
    save_login_state(state_root, LoginState(pid=42))
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(login, "_executable", lambda: "/bin/cloudflared")
    monkeypatch.setattr(login, "_is_login_process", lambda pid: False)
    monkeypatch.setattr(login, "_authenticated", lambda executable: False)
    monkeypatch.setattr(
        "sk_cloudflared.login.os.kill", lambda pid, signal: signals.append((pid, signal))
    )

    result = login.stop()

    assert result.status == "ok"
    assert signals == []
    assert load_login_state(state_root) is None


def test_stop_terminates_only_verified_monito_login(monkeypatch, tmp_path: Path) -> None:
    login = service(tmp_path)
    state_root = tmp_path / "monito" / "cloudflared"
    save_login_state(state_root, LoginState(pid=42))
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(login, "_executable", lambda: "/bin/cloudflared")
    monkeypatch.setattr(login, "_is_login_process", lambda pid: pid == 42)
    monkeypatch.setattr(login, "_authenticated", lambda executable: False)
    monkeypatch.setattr(login, "_wait_stopped", lambda pid: True)
    monkeypatch.setattr(
        "sk_cloudflared.login.os.kill", lambda pid, signal: signals.append((pid, signal))
    )

    result = login.stop()

    assert result.status == "ok"
    assert signals == [(42, 15)]
    assert load_login_state(state_root) is None
