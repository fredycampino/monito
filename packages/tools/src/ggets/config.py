"""Load one global configuration without exposing its contents in errors."""

import json
import os
from pathlib import Path


def load_config():
    explicit = os.environ.get("GGETS_CONFIG_FILE")
    path = Path(explicit).expanduser() if explicit else Path.home() / ".monito/ggets/config.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if not explicit:
            return {}
        raise ValueError("Configuration file not found") from None
    except (OSError, ValueError):
        raise ValueError("Cannot read a valid JSON configuration") from None
    if not isinstance(value, dict):
        raise ValueError("Configuration must be a JSON object")
    return value
