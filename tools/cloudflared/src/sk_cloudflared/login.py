import json
import os
import shutil
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from sk_cloudflared.config import cloudflared_home, state_dir
from sk_cloudflared.state import (
    LoginState,
    clear_login_state,
    load_login_state,
    login_log_path,
    save_login_state,
)


@dataclass(frozen=True)
class LoginResult:
    status: str
    cloudflared: str | None
    authenticated: bool
    running: bool
    pid: int | None
    state_path: str
    log_path: str
    cert_path: str
    message: str

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @property
    def ok(self) -> bool:
        return self.status == "ok"


class LoginService:
    def __init__(self, state_root: Path | None = None, cert_root: Path | None = None) -> None:
        self._state_dir = state_root or state_dir()
        self._cert_path = (cert_root or cloudflared_home()) / "cert.pem"

    def start(self) -> LoginResult:
        executable = self._executable()
        if executable is None:
            return self._result(
                status="error",
                cloudflared=None,
                authenticated=False,
                running=False,
                pid=None,
                message="cloudflared is not installed or not available on PATH",
            )
        if self._authenticated(executable):
            self._clear_stale_state()
            return self._result(
                status="ok",
                cloudflared=executable,
                authenticated=True,
                running=False,
                pid=None,
                message="Cloudflare login is already complete",
            )
        running_pid = self._managed_login_pid()
        if running_pid is not None:
            return self._result(
                status="ok",
                cloudflared=executable,
                authenticated=False,
                running=True,
                pid=running_pid,
                message="Cloudflare login is awaiting human authorization",
            )

        self._state_dir.mkdir(parents=True, exist_ok=True)
        log_path = login_log_path(self._state_dir)
        with log_path.open("a", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                [executable, "tunnel", "login"],
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        if process.poll() is not None:
            return self._result(
                status="error",
                cloudflared=executable,
                authenticated=False,
                running=False,
                pid=None,
                message=f"cloudflared login exited immediately with code {process.returncode}",
            )
        save_login_state(self._state_dir, LoginState(pid=process.pid))
        return self._result(
            status="ok",
            cloudflared=executable,
            authenticated=False,
            running=True,
            pid=process.pid,
            message="Complete Cloudflare authorization in the browser opened by cloudflared",
        )

    def status(self) -> LoginResult:
        executable = self._executable()
        if executable is None:
            self._clear_stale_state()
            return self._result(
                status="error",
                cloudflared=None,
                authenticated=False,
                running=False,
                pid=None,
                message="cloudflared is not installed or not available on PATH",
            )
        authenticated = self._authenticated(executable)
        running_pid = self._managed_login_pid()
        if authenticated:
            self._clear_stale_state()
            running_pid = None
        return self._result(
            status="ok",
            cloudflared=executable,
            authenticated=authenticated,
            running=running_pid is not None,
            pid=running_pid,
            message=(
                "Cloudflare login is complete"
                if authenticated
                else "Cloudflare login is awaiting human authorization"
                if running_pid is not None
                else "Cloudflare login is required"
            ),
        )

    def stop(self) -> LoginResult:
        executable = self._executable()
        state = load_login_state(self._state_dir)
        pid = state.pid if state else None
        if pid is None or not self._is_login_process(pid):
            self._clear_stale_state()
            authenticated = (
                self._authenticated(executable) if executable else self._cert_path.exists()
            )
            return self._result(
                status="ok",
                cloudflared=executable,
                authenticated=authenticated,
                running=False,
                pid=None,
                message="No Monito-managed Cloudflare login process is running",
            )

        os.kill(pid, signal.SIGTERM)
        if not self._wait_stopped(pid):
            return self._result(
                status="error",
                cloudflared=executable,
                authenticated=(
                    self._authenticated(executable) if executable else self._cert_path.exists()
                ),
                running=True,
                pid=pid,
                message=f"Cloudflare login process did not stop cleanly: pid={pid}",
            )
        clear_login_state(self._state_dir)
        return self._result(
            status="ok",
            cloudflared=executable,
            authenticated=(
                self._authenticated(executable) if executable else self._cert_path.exists()
            ),
            running=False,
            pid=None,
            message="Monito-managed Cloudflare login process stopped",
        )

    def _result(self, **values: object) -> LoginResult:
        return LoginResult(
            state_path=str(self._state_dir / "login.json"),
            log_path=str(login_log_path(self._state_dir)),
            cert_path=str(self._cert_path),
            **values,
        )

    def _executable(self) -> str | None:
        return shutil.which("cloudflared")

    def _authenticated(self, executable: str | None) -> bool:
        if self._cert_path.exists():
            return True
        if executable is None:
            return False
        result = subprocess.run(
            [executable, "tunnel", "list", "--output", "json"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0

    def _managed_login_pid(self) -> int | None:
        state = load_login_state(self._state_dir)
        if state is None or not self._is_login_process(state.pid):
            self._clear_stale_state()
            return None
        return state.pid

    def _clear_stale_state(self) -> None:
        clear_login_state(self._state_dir)

    def _is_login_process(self, pid: int) -> bool:
        if not self._pid_alive(pid):
            return False
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "args="],
            capture_output=True,
            text=True,
            check=False,
        )
        args = result.stdout.strip()
        return result.returncode == 0 and "cloudflared" in args and "tunnel login" in args

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _wait_stopped(self, pid: int) -> bool:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if not self._pid_alive(pid):
                return True
            time.sleep(0.1)
        return False
