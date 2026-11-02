"""Exercise the delivery command without a Runtime DB or external services."""

import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def delivery_step():
    flow = yaml.safe_load((ROOT / "packages/webhook/webhook.yaml").read_text())
    return next(step for step in flow["steps"] if step.get("shell") == "deliver_event")


def test_delivery_command_preserves_exit_status_across_invocations(tmp_path):
    step = delivery_step()
    assert step["check"] is False
    assert step["next"] == "wait_message"
    assert step["timeout"] == 45
    assert "timeout --kill-after=5s 30s skiller input receive" in step["command"]
    executable = tmp_path / "skiller"
    executable.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
        'if [ "$WEBHOOK_EVENT" = "first" ]; then\n'
        '  echo "subscriber unavailable" >&2\n  exit 7\nfi\n'
        'printf "delivered\\n"\n'
    )
    executable.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "CALL_LOG": str(tmp_path / "calls"),
        "SUBSCRIBER_RUN_ID": "isolated-subscriber",
        "NOTIFICATION_LABELS": "[Test]",
    }
    results = [
        subprocess.run(
            ["bash", "-c", step["command"]],
            env={**env, "WEBHOOK_EVENT": event},
            cwd=tmp_path, capture_output=True, text=True, timeout=5,
        )
        for event in ("first", "second")
    ]
    assert results[0].returncode == 7
    assert "subscriber unavailable" in results[0].stderr
    assert results[1].returncode == 0
    assert results[1].stdout == "delivered\n"
    calls = (tmp_path / "calls").read_text()
    assert calls.count("input receive") == 2
    assert calls.count("first") == 1
    assert calls.count("second") == 1


def test_delivery_internal_timeout_returns_nonzero(tmp_path):
    step = delivery_step()
    executable = tmp_path / "skiller"
    executable.write_text('#!/bin/sh\nexec sleep 10\n')
    executable.chmod(0o755)
    # Shorten only the internal deadline to keep this regression test fast.
    command = step["command"].replace("30s skiller", "0.1s skiller")
    result = subprocess.run(
        ["bash", "-c", command],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "SUBSCRIBER_RUN_ID": "isolated-subscriber",
            "NOTIFICATION_LABELS": "[Test]",
            "WEBHOOK_EVENT": "timeout",
        },
        cwd=tmp_path, capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 124
