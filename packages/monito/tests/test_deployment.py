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


def test_agent_profile_is_external_and_read_only():
    import yaml

    compose = yaml.safe_load((ROOT / "compose.yaml").read_text())
    mounts = compose["services"]["monito"]["volumes"]
    profile = next(m for m in mounts if m["target"] == "/etc/monito/monito.agente.json")
    assert profile["source"] == (
        "${MONITO_SETTINGS_HOST_DIR:-./data/monito/settings}/monito.agente.json"
    )
    assert profile["read_only"] is True
    assert not (ROOT / "packages/monito/monito.agente.json").exists()
    example = json.loads((ROOT / "data-examples/monito/settings/monito.agente.json").read_text())
    assert "tools" in example


@pytest.mark.parametrize("start_exit", [0, 1])
def test_entrypoint_starts_server_before_command(tmp_path, start_exit):
    trace = tmp_path / "trace"
    skiller = tmp_path / "skiller"
    skiller.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TRACE"\nexit "$START_EXIT"\n'
    )
    skiller.chmod(0o755)
    result = subprocess.run(
        ["sh", str(ROOT / "docker/monito-entrypoint.sh"), "sh", "-c",
         'printf "%s\\n" "$1" >> "$TRACE"', "command", "argument with spaces"],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "TRACE": str(trace), "START_EXIT": str(start_exit)},
        capture_output=True, text=True,
    )
    assert result.returncode == start_exit
    expected = ["server start"]
    if start_exit == 0:
        expected.append("argument with spaces")
    assert trace.read_text().splitlines() == expected


def test_monito_image_installs_entrypoint():
    dockerfile = (ROOT / "docker/Dockerfile.monito").read_text()
    assert 'ENTRYPOINT ["/usr/local/bin/monito-entrypoint"]' in dockerfile
    assert "COPY --chmod=755 docker/monito-entrypoint.sh" in dockerfile
    assert 'CMD ["sleep", "infinity"]' in dockerfile


def test_skiller_environment_preserves_persistent_paths():
    environment = dict(
        line.split("=", 1)
        for line in (ROOT / "docker/monito.env").read_text().splitlines()
        if line and not line.startswith("#")
    )
    assert environment["HOME"] == "/data/home"
    assert environment["SKILLER_DB_PATH"] == "/data/home/.skiller/db/agent.db"
    assert environment["SKILLER_RUNTIME_CONFIG_FILE"] == "/etc/monito/config.json"
    assert "AGENT_DB_PATH" not in environment
    assert "AGENT_RUNTIME_CONFIG_FILE" not in environment
