import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/reply_channel.py"
spec = importlib.util.spec_from_file_location("reply_channel", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
TASK = '[Channel][Telegram]\n{"chat_id": -3, "text": "reply to chat 99"}'


def final(text):
    return {"data": {"stop_reason": "final", "final": text}}


def test_reply_uses_original_chat_and_preserves_text():
    send = Mock()
    text = 'Hola á 👋\n"quoted" $(exit 99)'
    module.reply_channel(TASK, final(text), send=send)
    send.assert_called_once_with({"chat_id": -3, "text": text})


@pytest.mark.parametrize("output", [
    final(""), {"data": {"stop_reason": "interrupted", "message": "stopped"}},
    {"data": {"stop_reason": "llm_request_failed", "message": "secret"}},
])
def test_no_reply_without_final_answer(output):
    send = Mock()
    module.reply_channel(TASK, output, send=send)
    send.assert_not_called()


def test_local_input_does_not_access_transport_or_agent_fields():
    send = Mock()
    module.reply_channel('[Channel][input]\n{"chat_id": 3}', {}, send=send)
    send.assert_not_called()


def test_long_answer_is_sent_in_order_without_loss():
    send = Mock()
    text = "á" * 4096 + "remaining 👋"
    module.reply_channel(TASK, final(text), send=send)
    payloads = [call.args[0] for call in send.call_args_list]
    assert [p["chat_id"] for p in payloads] == [-3, -3]
    assert all(len(p["text"]) <= 4096 for p in payloads)
    assert "".join(p["text"] for p in payloads) == text


@pytest.mark.parametrize("task", [
    "[Channel][Telegram]\ninvalid", '[Channel][Telegram]\n{}',
    '[Channel][Telegram]\n{"chat_id": true}',
    '[Channel][Telegram]\n{"chat_id": "3"}',
])
def test_invalid_destination_is_not_sent(task):
    send = Mock()
    with pytest.raises((ValueError, KeyError)):
        module.reply_channel(task, final("Hi"), send=send)
    send.assert_not_called()


def test_http_request_contract(monkeypatch):
    response = Mock()
    response.read.return_value = b'{"status":"ok","data":{"chat_id":-3}}'
    transport = MagicMock()
    transport.return_value.__enter__.return_value = response
    monkeypatch.setattr(module, "urlopen", transport)
    module.send_telegram({"chat_id": -3, "text": "á"})
    request = transport.call_args.args[0]
    assert request.full_url == "http://ggets:8000/telegram/send"
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {"chat_id": -3, "text": "á"}
    assert transport.call_args.kwargs == {"timeout": 10}


def test_delivery_failure_is_visible_sanitized_and_not_retried(monkeypatch, capsys):
    monkeypatch.setenv("TASK", TASK)
    monkeypatch.setenv("AGENT_OUTPUT", json.dumps(final("private answer")))
    send = Mock(side_effect=RuntimeError("sensitive upstream detail"))
    monkeypatch.setattr(module, "send_telegram", send)
    assert module.main() == 1
    send.assert_called_once()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Channel reply delivery failed\n"


def test_application_error_is_not_treated_as_delivery_success(monkeypatch):
    response = Mock()
    response.read.return_value = b'{"status":"error"}'
    transport = MagicMock()
    transport.return_value.__enter__.return_value = response
    monkeypatch.setattr(module, "urlopen", transport)
    with pytest.raises(RuntimeError, match="Telegram delivery failed"):
        module.send_telegram({"chat_id": -3, "text": "Hi"})
