import os
import shutil
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


def load_local_config() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=Path(dotenv_path), override=False)


def skiller_executable() -> str | None:
    configured = os.environ.get("SKILLER_BIN", "").strip()
    return shutil.which(configured or "skiller")
