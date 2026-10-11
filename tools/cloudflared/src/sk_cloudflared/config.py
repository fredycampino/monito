import os
from pathlib import Path


def monito_home() -> Path:
    configured = os.environ.get("MONITO_HOME", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".monito"


def state_dir() -> Path:
    return monito_home() / "cloudflared"


def cloudflared_home() -> Path:
    return Path.home() / ".cloudflared"
