import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from skiller.application.use_cases.flow.flow_checker import FlowCheckerUseCase
from skiller.infrastructure.flow.flow_yaml_mapper import FlowYamlMapper

ROOT = Path(__file__).resolve().parents[1]
FLOW = yaml.safe_load((ROOT / "monito.yaml").read_text())


@pytest.mark.parametrize("task,expected", [
    ("Hola", "[Channel][input]\nHola"),
    ("", "[Channel][input]\n"),
    ('línea\n$(exit 99) "texto"\n', '[Channel][input]\nlínea\n$(exit 99) "texto"\n'),
    ('[Channel][Telegram]\n{"chat_id": 3, "text": "Hi"}',
     '[Channel][Telegram]\n{"chat_id": 3, "text": "Hi"}'),
    ('[Notification][Telegram]\n{}', '[Channel][input]\n[Notification][Telegram]\n{}'),
    ('texto [Channel][Telegram]\n{}', '[Channel][input]\ntexto [Channel][Telegram]\n{}'),
])
def test_task_mapping(task, expected):
    step = next(step for step in FLOW["steps"] if step.get("shell") == "map_channel")
    command = step["command"].replace("{{runtime.python}}", sys.executable).replace(
        "{{flow.dir}}", str(ROOT)
    )
    result = subprocess.run(
        ["sh", "-c", command], cwd=ROOT, env={**os.environ, "TASK": task},
        capture_output=True, text=True, check=True,
    )
    assert result.stdout == expected
    assert result.stderr == ""
    assert step["env"] == {"TASK": '{{output_value("ask_user").payload.text}}'}


def test_flow_routes_mapped_task_to_agent():
    class FlowPort:
        def get_yaml_flow(self, path):
            return FlowYamlMapper().to_flow(yaml.safe_load(path.read_text()))

    result = FlowCheckerUseCase(FlowPort()).execute(ROOT / "monito.yaml")
    assert not result.errors
    steps = FLOW["steps"]
    assert steps[0]["next"] == "map_channel"
    assert steps[1]["next"] == "inprogress"
    progress = steps[2]
    assert progress["shell"] == "inprogress"
    assert progress["env"] == {"TASK": '{{output_value("map_channel").stdout}}'}
    assert progress["check"] is False
    assert progress["next"] == "monito"
    assert steps[3]["task"] == '{{output_value("map_channel").stdout}}'
    assert steps[3]["next"] == "reply_channel"
    reply = steps[4]
    assert reply["shell"] == "reply_channel"
    assert reply["env"] == {
        "TASK": '{{output_value("map_channel").stdout}}',
        "AGENT_OUTPUT": '{{output_value("monito")}}',
    }
    assert reply["check"] is False
    assert reply["next"] == "ask_user"
