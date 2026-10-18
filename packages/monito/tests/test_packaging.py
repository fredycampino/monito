import json
import tomllib
from pathlib import Path

from skiller.application.use_cases.flow.resolve_flow import (
    ResolveFlowInput,
    ResolveFlowStatus,
    ResolveFlowUseCase,
)
from skiller.domain.flow.flow_reference import FlowReference

ROOT = Path(__file__).resolve().parents[3]


def test_wheel_resources_mirror_repository():
    project = tomllib.loads((ROOT / "packages/monito/pyproject.toml").read_text())
    included = project["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    for source, destination in included.items():
        original = (ROOT / "packages/monito" / source).resolve()
        assert destination == original.relative_to(ROOT).as_posix()
        assert original.exists()


def test_short_references_resolve_from_mirror():
    resolver = ResolveFlowUseCase(home_path=ROOT)
    for name in ("monito", "webhook"):
        result = resolver.execute(ResolveFlowInput(
            reference=FlowReference(f"@{name}"), flow_paths=(ROOT / "packages",)
        ))
        assert result.status == ResolveFlowStatus.RESOLVED
        assert result.flow.flow_path == ROOT / "packages" / name / f"{name}.yaml"


def test_runtime_example_uses_mirror_root():
    config = json.loads((ROOT / "data-examples/monito/settings/config.json").read_text())
    assert config["flow_paths"] == [
        "/usr/local/lib/python3.12/site-packages/packages"
    ]


def test_telegram_instruction_is_loaded():
    import yaml

    root = ROOT / "packages/monito"
    flow = yaml.safe_load((root / "monito.yaml").read_text())
    agent = next(step for step in flow["steps"] if step.get("agent") == "monito")
    reference = "./instructions/use-telegram.md"
    assert reference in agent["instructions"]
    assert (root / reference).is_file()


def test_webhook_delivery_uses_workspace_cwd():
    import yaml

    flow = yaml.safe_load((ROOT / "packages/webhook/webhook.yaml").read_text())
    delivery = next(step for step in flow["steps"] if step.get("shell") == "deliver_event")
    assert delivery["cwd"] == "/data/workspace"
