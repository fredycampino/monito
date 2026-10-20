import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml
from skiller.application.use_cases.flow.flow_checker import FlowCheckerUseCase
from skiller.infrastructure.flow.flow_yaml_mapper import FlowYamlMapper

ROOT = Path(__file__).resolve().parents[1]
FLOW = yaml.safe_load((ROOT / "webhook.yaml").read_text())


def test_flow_structure():
    class FlowPort:
        def get_yaml_flow(self, path):
            return FlowYamlMapper().to_flow(yaml.safe_load(path.read_text()))

    result = FlowCheckerUseCase(FlowPort()).execute(ROOT / "webhook.yaml")
    assert not result.errors
    assert FLOW["start"] == "register_webhook"
    assert len(FLOW["steps"]) == 3
    assert FLOW["steps"][1]["wait_webhook"] == "wait_message"
    assert set(FLOW["inputs"]) == {"run_id", "webhook", "key", "labels"}
    assert FLOW["steps"][1]["key"] == "{{inputs.key}}"
    assert FLOW["steps"][1]["webhook"] == "{{inputs.webhook}}"
    assert FLOW["steps"][2]["next"] == "wait_message"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        None,
        {"text": ""},
        {"text": "Hola"},
        {"text": '$(exit 99) "quoted"\nUnicode á', "chat_id": 42},
    ],
)
def test_forwards_entire_payload(payload, tmp_path):
    executable = tmp_path / "skiller"
    executable.write_text('#!/bin/sh\nprintf "%s\\0" "$@"\n')
    executable.chmod(0o755)
    event = json.dumps(payload, ensure_ascii=False)
    command = FLOW["steps"][2]["command"]
    result = subprocess.run(
        ["bash", "-c", command],
        env={
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "SUBSCRIBER_RUN_ID": "subscriber",
            "WEBHOOK_EVENT": event,
            "NOTIFICATION_LABELS": "[Notification][Telegram]",
        },
        capture_output=True,
        check=True,
    )
    assert result.stdout.decode().split("\0") == [
        "input",
        "receive",
        "subscriber",
        "--text=[Notification][Telegram]\n" + event,
        "",
    ]


def test_failure_is_not_hidden(tmp_path):
    executable = tmp_path / "skiller"
    executable.write_text("#!/bin/sh\nexit 1\n")
    executable.chmod(0o755)
    result = subprocess.run(
        ["bash", "-c", FLOW["steps"][2]["command"]],
        env={
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "SUBSCRIBER_RUN_ID": "subscriber",
            "WEBHOOK_EVENT": "{}",
            "NOTIFICATION_LABELS": "[Notification][Telegram]",
        },
    )
    assert result.returncode == 1


@pytest.mark.parametrize(
    "status,cli_exit,expected",
    [
        ("REGISTERED", 0, 0),
        ("ALREADY_REGISTERED", 1, 0),
        ("INVALID_CONFIG", 1, 1),
        ("unexpected", 0, 1),
    ],
)
def test_registration(status, cli_exit, expected):
    import sys

    command = FLOW["steps"][0]["command"].replace("{{runtime.python}}", sys.executable)
    response = json.dumps({"status": status, "secret": "must-not-be-printed"})
    result = subprocess.run(
        ["bash", "-c", 'skiller() { printf "%s" "$RESPONSE"; return "$CLI_EXIT"; };\n' + command],
        env={"WEBHOOK_NAME": "telegram", "RESPONSE": response, "CLI_EXIT": str(cli_exit)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == expected
    assert "must-not-be-printed" not in result.stdout
    assert FLOW["steps"][0]["next"] == "wait_message"
