from importlib.resources import files

import yaml
from monito.cli import flow_path
from skiller.domain.agent.instruction_reference import is_packaged_instruction


def test_flow():
    root = flow_path().parent
    flow = yaml.safe_load(root.joinpath("monito.yaml").read_text())
    assert flow["start"] == "ask_user"
    assert root.joinpath("system.md").is_file()
    agent = next(step for step in flow["steps"] if step.get("agent") == "monito")
    assert "./instructions/use-telegram.md" in agent["instructions"]
    assert "./instructions/style-response.md" in agent["instructions"]
    for reference in agent["instructions"]:
        if is_packaged_instruction(reference):
            assert files("apps").joinpath("instructions", f"{reference}.md").is_file()
        else:
            assert (root / reference).is_file()
    assert agent["config"] == {"file": "/etc/monito/agent.json"}
    assert (root / agent["system"]["file"]).is_file()
