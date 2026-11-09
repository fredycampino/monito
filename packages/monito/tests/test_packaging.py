import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from skiller.application.use_cases.flow.resolve_flow import (
    ResolveFlowInput,
    ResolveFlowStatus,
    ResolveFlowUseCase,
)
from skiller.domain.flow.flow_reference import FlowReference

ROOT = Path(__file__).resolve().parents[3]


def test_built_wheel_contains_usable_flow_resources(tmp_path):
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation",
         "--outdir", str(tmp_path), str(ROOT / "packages/monito")],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    with ZipFile(next(tmp_path.glob("*.whl"))) as wheel:
        for name in (
            "monito.yaml", "system.md", "scripts/map_channel.py", "scripts/reply_channel.py",
            "scripts/inprogress.py",
        ):
            path = "packages/monito/" + name
            assert wheel.read(path) == (ROOT / path).read_bytes()
        for instruction in (ROOT / "packages/monito/instructions").glob("*.md"):
            path = instruction.relative_to(ROOT).as_posix()
            assert wheel.read(path) == instruction.read_bytes()
        path = "packages/webhook/webhook.yaml"
        assert wheel.read(path) == (ROOT / path).read_bytes()
        wheel.extractall(tmp_path / "installed")
    # Run outside the checkout, using only the wheel's extracted resources.
    installed = tmp_path / "installed"
    result = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); "
         "from monito.cli import flow_path; print(flow_path())", str(installed)],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert Path(result.stdout.strip()) == installed / "packages/monito/monito.yaml"
    result = subprocess.run(
        [sys.executable, str(installed / "packages/monito/scripts/map_channel.py")],
        cwd=tmp_path, env={"TASK": "Hola"}, capture_output=True, text=True, check=True,
    )
    assert result.stdout == "[Channel][input]\nHola"


def test_short_references_resolve_from_mirror():
    resolver = ResolveFlowUseCase(home_path=ROOT)
    for name in ("monito", "webhook"):
        result = resolver.execute(ResolveFlowInput(
            reference=FlowReference(f"@{name}"), flow_paths=(ROOT / "packages",)
        ))
        assert result.status == ResolveFlowStatus.RESOLVED
        assert result.flow.flow_path == ROOT / "packages" / name / f"{name}.yaml"


def test_runtime_example_declares_deployment_placeholders():
    config = json.loads((ROOT / "data-examples/monito/settings/config.json").read_text())
    assert config["flow_paths"] == ["${MONITO_FLOW_PATH}"]
    assert config["webhooks"] == {"host": "${MONITO_INTERNAL_IP}", "port": 8001}


def test_webhook_delivery_uses_workspace_cwd():
    import yaml

    flow = yaml.safe_load((ROOT / "packages/webhook/webhook.yaml").read_text())
    delivery = next(step for step in flow["steps"] if step.get("shell") == "deliver_event")
    assert delivery["cwd"] == "/data/workspace"


def test_ggets_example_declares_deployment_placeholders():
    config = json.loads((ROOT / "data-examples/ggets/config.json").read_text())
    assert config["server"] == {"host": "${GGETS_INTERNAL_IP}", "port": 8000}
    assert config["telegram"]["receiver_host"] == "${GGETS_TELEGRAM_IP}"
    assert config["telegram"]["receiver_port"] == "${GGETS_TELEGRAM_PORT}"
