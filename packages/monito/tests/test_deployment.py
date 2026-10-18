import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker Compose required")
@pytest.mark.parametrize("prefix,version", [
    ("", "dev"),
    ("ghcr.io/fredycampino/", "0.1.0-beta.5"),
    ("ghcr.io/fredycampino/", "0.1.0-beta.4"),
])
def test_shared_image_selection(prefix, version):
    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=ROOT,
        env={**os.environ, "IMAGE_PREFIX": prefix, "RELEASE_VERSION": version},
        capture_output=True, text=True, check=True,
    )
    config = json.loads(result.stdout)
    for service, image in [("monito", "monito-box"), ("ggets", "ggets")]:
        assert config["services"][service]["image"] == f"{prefix}{image}:{version}"
