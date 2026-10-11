import json
import os
import re
import shutil
import signal
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from sk_cloudflared.config import state_dir
from sk_cloudflared.login import LoginService

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,62}$")


@dataclass(frozen=True)
class TunnelState:
    name: str
    config_path: str
    pid: int | None = None


@dataclass(frozen=True)
class TunnelResult:
    status: str
    name: str
    config_path: str | None
    running: bool
    managed: bool
    pid: int | None
    state_path: str
    message: str

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass(frozen=True)
class TunnelListResult:
    status: str
    tunnels: list[dict[str, object]]
    message: str

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def as_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class TunnelService:
    def __init__(self, state_root: Path | None = None, login: LoginService | None = None) -> None:
        self._state_root = state_root or state_dir()
        self._login = login or LoginService()

    def register(self, name: str, config_path: str) -> TunnelResult:
        if not _NAME.fullmatch(name):
            return self._error(
                name, "Tunnel name must contain only letters, numbers, underscores, or hyphens"
            )
        config = Path(config_path).expanduser()
        if not config.is_file():
            return self._error(name, "Provided Cloudflared configuration file does not exist")
        existing = self._load(name)
        if existing is not None and existing.config_path != str(config):
            return self._error(
                name, "Tunnel is already registered with another configuration path", existing
            )
        state = existing or TunnelState(name=name, config_path=str(config))
        self._save(state)
        return self._result("ok", state, False, None, "Tunnel configuration registered")

    def open(self, name: str) -> TunnelResult:
        state = self._load(name)
        if state is None:
            return self._error(name, "Tunnel is not registered; run tunnel register first")
        if self._managed_pid(state) is not None:
            return self._result("ok", state, True, state.pid, "Tunnel connector is already running")
        executable = self._executable()
        if executable is None:
            return self._error(name, "cloudflared is not installed or not available on PATH", state)
        if not Path(state.config_path).is_file():
            return self._error(
                name, "Registered Cloudflared configuration file no longer exists", state
            )
        process = subprocess.Popen(
            [executable, "tunnel", "--config", state.config_path, "run"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if process.poll() is not None:
            return self._error(
                name, f"Tunnel connector exited immediately with code {process.returncode}", state
            )
        running = TunnelState(name=state.name, config_path=state.config_path, pid=process.pid)
        self._save(running)
        return self._result("ok", running, True, process.pid, "Tunnel connector started")

    def status(self, name: str) -> TunnelResult:
        state = self._load(name)
        if state is None:
            return self._error(name, "Tunnel is not registered")
        pid = self._managed_pid(state)
        if state.pid is not None and pid is None:
            state = TunnelState(name=state.name, config_path=state.config_path)
            self._save(state)
        return self._result(
            "ok",
            state,
            pid is not None,
            pid,
            "Tunnel connector is running" if pid else "Tunnel connector is stopped",
        )

    def close(self, name: str) -> TunnelResult:
        state = self._load(name)
        if state is None:
            return self._error(name, "Tunnel is not registered")
        pid = self._managed_pid(state)
        if pid is None:
            stopped = TunnelState(name=state.name, config_path=state.config_path)
            self._save(stopped)
            return self._result(
                "ok", stopped, False, None, "No Monito-managed tunnel connector is running"
            )
        os.kill(pid, signal.SIGTERM)
        if not self._wait_stopped(pid):
            return self._result("error", state, True, pid, "Tunnel connector did not stop cleanly")
        stopped = TunnelState(name=state.name, config_path=state.config_path)
        self._save(stopped)
        return self._result("ok", stopped, False, None, "Monito-managed tunnel connector stopped")

    def list(self) -> TunnelListResult:
        executable = self._executable()
        if executable is None:
            return TunnelListResult(
                "error", [], "cloudflared is not installed or not available on PATH"
            )
        if not self._login.status().authenticated:
            return TunnelListResult(
                "error", [], "Cloudflare login is required; run sk-cloudflared login start"
            )
        result = subprocess.run(
            [executable, "tunnel", "list", "--output", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            payload = json.loads(result.stdout) if result.returncode == 0 else None
        except json.JSONDecodeError:
            payload = None
        if not isinstance(payload, list):
            return TunnelListResult("error", [], "Cloudflare tunnel list could not be read")
        tunnels = [item for item in payload if isinstance(item, dict)]
        return TunnelListResult("ok", tunnels, "Remote tunnels listed")

    @staticmethod
    def _executable() -> str | None:
        return shutil.which("cloudflared")

    def _state_path(self, name: str) -> Path:
        return self._state_root / "tunnels" / f"{name}.json"

    def _load(self, name: str) -> TunnelState | None:
        try:
            payload = json.loads(self._state_path(name).read_text(encoding="utf-8"))
            return TunnelState(**payload)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _save(self, state: TunnelState) -> None:
        path = self._state_path(state.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(state)), encoding="utf-8")

    def _managed_pid(self, state: TunnelState) -> int | None:
        if state.pid is None or not self._pid_alive(state.pid):
            return None
        result = subprocess.run(
            ["ps", "-p", str(state.pid), "-o", "args="], capture_output=True, text=True, check=False
        )
        args = result.stdout.strip()
        expected = f"--config {state.config_path} run"
        return (
            state.pid
            if result.returncode == 0 and "cloudflared" in args and expected in args
            else None
        )

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

    def _result(
        self, status: str, state: TunnelState, running: bool, pid: int | None, message: str
    ) -> TunnelResult:
        return TunnelResult(
            status,
            state.name,
            state.config_path,
            running,
            running,
            pid,
            str(self._state_path(state.name)),
            message,
        )

    def _error(self, name: str, message: str, state: TunnelState | None = None) -> TunnelResult:
        return TunnelResult(
            "error",
            name,
            state.config_path if state else None,
            False,
            False,
            None,
            str(self._state_path(name)),
            message,
        )
