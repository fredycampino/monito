from pathlib import Path

DEFAULT_STATE_FILE = Path.home() / ".local" / "state" / "monito" / "telegram" / "offset"


def load_offset(state_file: Path) -> int | None:
    if not state_file.exists():
        return None

    value = state_file.read_text(encoding="utf-8").strip()
    if not value:
        return None

    return int(value)


def save_offset(state_file: Path, offset: int) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(str(offset), encoding="utf-8")
