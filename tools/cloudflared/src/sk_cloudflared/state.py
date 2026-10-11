import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoginState:
    pid: int


def login_state_path(state_dir: Path) -> Path:
    return state_dir / "login.json"


def login_log_path(state_dir: Path) -> Path:
    return state_dir / "login.log"


def load_login_state(state_dir: Path) -> LoginState | None:
    path = login_state_path(state_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pid = payload.get("pid") if isinstance(payload, dict) else None
    return LoginState(pid=pid) if isinstance(pid, int) and pid > 0 else None


def save_login_state(state_dir: Path, state: LoginState) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    login_state_path(state_dir).write_text(json.dumps({"pid": state.pid}), encoding="utf-8")


def clear_login_state(state_dir: Path) -> None:
    login_state_path(state_dir).unlink(missing_ok=True)
