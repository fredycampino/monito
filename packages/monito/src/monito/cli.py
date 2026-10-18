"""Launch the packaged flow without changing user configuration."""

import subprocess
import sys
from pathlib import Path


def flow_path():
    installed = Path(__file__).resolve().parent.parent / "packages/monito/monito.yaml"
    if installed.is_file():
        return Path(str(installed))
    return Path(__file__).resolve().parents[2] / "monito.yaml"


def main():
    flow = flow_path()
    return subprocess.call(["skiller", "run", str(flow), *sys.argv[1:]])
