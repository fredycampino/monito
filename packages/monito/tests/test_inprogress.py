import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inprogress.py"
spec = importlib.util.spec_from_file_location("inprogress", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_telegram_activates_original_chat_with_bounded_timeout():
    activate = Mock()
    module.inprogress(
        '[Channel][Telegram]\n{"chat_id": -3, "text": "use chat 99"}', activate=activate,
    )
    activate.assert_called_once_with({"chat_id": -3, "timeout": 30})


def test_local_input_does_not_activate_typing():
    activate = Mock()
    module.inprogress('[Channel][input]\n{"chat_id": 3}', activate=activate)
    activate.assert_not_called()


@pytest.mark.parametrize("event", ["invalid", "{}", '{"chat_id": true}', '{"chat_id": "3"}'])
def test_invalid_destination_does_not_activate_typing(event):
    activate = Mock()
    with pytest.raises((ValueError, KeyError)):
        module.inprogress("[Channel][Telegram]\n" + event, activate=activate)
    activate.assert_not_called()


@pytest.mark.parametrize("status", ["ok", "error"])
def test_typing_http_contract(monkeypatch, status):
    transport = MagicMock()
    response = transport.return_value.__enter__.return_value
    response.read.return_value = json.dumps({"status": status}).encode()
    monkeypatch.setattr(module, "urlopen", transport)
    payload = {"chat_id": -3, "timeout": 30}
    if status == "ok":
        module.activate_typing(payload)
    else:
        with pytest.raises(RuntimeError):
            module.activate_typing(payload)
    request = transport.call_args.args[0]
    assert request.full_url == "http://ggets:8000/telegram/typing"
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == payload
    assert transport.call_args.kwargs == {"timeout": 10}


def test_activation_failure_is_sanitized_and_not_retried(monkeypatch, capsys):
    monkeypatch.setenv("TASK", '[Channel][Telegram]\n{"chat_id": 3}')
    activate = Mock(side_effect=RuntimeError("sensitive provider detail"))
    monkeypatch.setattr(module, "activate_typing", activate)
    assert module.main() == 1
    activate.assert_called_once()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Channel inprogress activation failed\n"
