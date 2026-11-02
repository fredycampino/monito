import threading
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ggets.telegram.business.typing import TypingService
from ggets.telegram.config import map_config
from ggets.telegram.help import OPERATIONS
from ggets.telegram.module import TelegramModule
from ggets.telegram.router import create_router
from ggets.telegram.schemas import SendInput, TypingInput
from ggets.telegram.service import TelegramService


@pytest.fixture
def typing():
    now = [0.0]
    client = Mock()
    service = TypingService(client, clock=lambda: now[0], chance=Mock(return_value=0.1))
    # Drive the same scheduler deterministically, without sleeps or networking.
    service.thread = Mock()
    yield service, client, now
    service.close()


def tick(service, now, value):
    now[0] = value
    service._tick()


def test_renew_skip_and_expire(typing):
    service, client, now = typing
    service.start(3, 30)
    client.call.assert_called_once_with("sendChatAction", {"chat_id": 3, "action": "typing"})
    tick(service, now, 3)
    assert client.call.call_count == 1
    tick(service, now, 4)
    assert client.call.call_count == 2
    service.chance.return_value = 0.9
    tick(service, now, 8)
    assert client.call.call_count == 2
    service.chance.return_value = 0.1
    tick(service, now, 12)
    assert client.call.call_count == 3
    tick(service, now, 30)
    assert not service.leases
    assert client.call.call_count == 3


def test_reply_at_seven_seconds_cancels_only_its_chat(typing):
    service, client, now = typing
    service.start(3, 30)
    service.start(4, 30)
    tick(service, now, 4)
    now[0] = 7
    send = Mock(return_value={"message_id": 1})
    assert service.send_message(SendInput(chat_id=3, text="Hi"), send) == {"message_id": 1}
    client.call.reset_mock()
    tick(service, now, 8)
    client.call.assert_called_once_with("sendChatAction", {"chat_id": 4, "action": "typing"})


def test_repeated_request_replaces_deadline(typing):
    service, client, now = typing
    service.start(3, 30)
    now[0] = 7
    service.start(3, 10)
    assert service.leases == {3: (17, 11)}
    tick(service, now, 17)
    assert not service.leases
    assert client.call.call_count == 2


def test_failures_and_cleanup(typing, caplog):
    service, client, now = typing
    client.call.side_effect = RuntimeError("sensitive")
    with pytest.raises(RuntimeError):
        service.start(3, 30)
    assert not service.leases
    client.call.side_effect = None
    service.start(3, 30)
    client.call.side_effect = RuntimeError("sensitive")
    tick(service, now, 4)
    assert "renewal failed" in caplog.text
    assert "sensitive" not in caplog.text
    with pytest.raises(RuntimeError):
        service.send_message(SendInput(chat_id=3, text="Hi"), Mock(side_effect=RuntimeError()))
    assert 3 in service.leases
    service.clear()
    assert not service.leases


def test_worker_shutdown():
    service = TypingService(Mock())
    service.start(3, 30)
    worker = service.thread
    service.start(4, 30)
    assert service.thread is worker
    service.close()
    assert not worker.is_alive()
    assert not service.leases


def test_reply_waits_for_inflight_renewal(typing):
    service, client, now = typing
    service.start(3, 30)
    entered, release, contended = threading.Event(), threading.Event(), threading.Event()
    sent = threading.Event()
    order = []

    def renew(*args):
        entered.set()
        assert release.wait(2)
        order.append("typing")

    def send(request):
        order.append("send")
        sent.set()

    class ObservedLock:
        def __init__(self, lock):
            self.lock = lock

        def acquire(self, blocking=True):
            if self.lock.acquire(blocking=False):
                return True
            contended.set()
            return self.lock.acquire() if blocking else False

        def release(self):
            self.lock.release()

    client.call.side_effect = renew
    renewal = threading.Thread(target=tick, args=(service, now, 4))
    response = threading.Thread(
        target=service.send_message, args=(SendInput(chat_id=3, text="Hi"), send),
    )
    renewal.start()
    try:
        assert entered.wait(2)
        with service.condition:
            lock, users = service.chat_locks[3]
            service.chat_locks[3] = (ObservedLock(lock), users)
        response.start()
        assert contended.wait(2), "Reply must actually contend with the renewal"
        assert not sent.is_set()
    finally:
        release.set()
        renewal.join(2)
        if response.ident is not None:
            response.join(2)
    assert not renewal.is_alive() and not response.is_alive()
    assert order == ["typing", "send"]
    assert not service.leases


@pytest.fixture
def http():
    config = map_config({
        "base_url": "https://example.com",
        "bot_father_token_file": "/unused/mock-token",
        "webhook_secret_file": "/unused/mock-secret",
    })
    service = TelegramService(config, client=Mock())
    app = FastAPI()
    app.include_router(create_router(service, OPERATIONS), prefix="/telegram")
    with TestClient(app) as client:
        yield client, service
    service.typing_actions.close()


def test_http_contract_and_reply(http):
    client, service = http
    response = client.post("/telegram/typing", json={"chat_id": 3, "timeout": 30})
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data": {"chat_id": 3}}
    service.client.call.return_value = {"chat": {"id": 3}, "message_id": 7}
    assert client.post("/telegram/send", json={"chat_id": 3, "text": "Hi"}).status_code == 200
    assert not service.typing_actions.leases
    assert "typing" in client.get("/telegram/help").json()["operations"]
    assert TypingInput(chat_id=3).timeout == 5


@pytest.mark.parametrize("body", [
    {}, {"chat_id": True}, {"chat_id": "3"}, {"chat_id": 3, "timeout": 0},
    {"chat_id": 3, "timeout": 121}, {"chat_id": 3, "timeout": 1.5},
    {"chat_id": 3, "timeout": True}, {"chat_id": 3, "extra": 1},
])
def test_http_invalid_input(http, body):
    client, service = http
    assert client.post("/telegram/typing", json=body).status_code == 422
    service.client.call.assert_not_called()


def test_http_initial_failure(http):
    client, service = http
    service.client.call.side_effect = RuntimeError("secret")
    response = client.post("/telegram/typing", json={"chat_id": 3})
    assert response.status_code == 502
    assert "secret" not in response.text
    assert not service.typing_actions.leases


def test_http_missing_configuration():
    service = TelegramService(map_config({}), client=Mock())
    app = FastAPI()
    app.include_router(create_router(service, ("typing",)), prefix="/telegram")
    response = TestClient(app).post("/telegram/typing", json={"chat_id": 3})
    assert response.status_code == 503
    service.client.call.assert_not_called()


def test_module_lifespan_stops_typing_worker(monkeypatch):
    from contextlib import nullcontext

    module = TelegramModule({}, ("typing",))
    monkeypatch.setattr("ggets.telegram.module.receiver_lifespan", lambda service: nullcontext())
    with module.lifespan():
        module.service.typing_actions.client = Mock()
        module.service.typing_actions.start(3, 30)
    assert not module.service.typing_actions.thread.is_alive()


def test_stop_clears_leases(http, monkeypatch):
    client, service = http
    service.subscription.store = Mock()
    service.subscription.store.load.return_value = None
    monkeypatch.setattr(service, "webhook", Mock(return_value=Mock()))
    assert client.post("/telegram/typing", json={"chat_id": 3, "timeout": 30}).status_code == 200
    assert client.post("/telegram/stop", json={}).status_code == 200
    assert not service.typing_actions.leases


def test_cli_does_not_advertise_persistent_typing():
    import argparse

    from ggets.telegram.cli import register_cli

    parser = argparse.ArgumentParser()
    register_cli(parser, Mock(), OPERATIONS)
    assert parser.parse_args(["send", "--json", '{}']).operation == "send"
    with pytest.raises(SystemExit):
        parser.parse_args(["typing"])


def test_slow_renewal_does_not_send_expired_next_chat(typing):
    service, client, now = typing
    service.start(3, 5)
    service.start(4, 5)
    client.call.reset_mock()

    def slow_renewal(*args):
        now[0] = 14

    client.call.side_effect = slow_renewal
    tick(service, now, 4)
    client.call.assert_called_once_with("sendChatAction", {"chat_id": 3, "action": "typing"})
    assert 4 not in service.leases


def test_slow_renewal_does_not_block_another_chats_reply(typing):
    service, client, now = typing
    service.start(3, 30)
    service.start(4, 30)
    entered, release, replied = threading.Event(), threading.Event(), threading.Event()

    def slow_renewal(*args):
        entered.set()
        release.wait(2)

    def reply():
        service.send_message(SendInput(chat_id=4, text="Hi"), Mock())
        replied.set()

    client.call.side_effect = slow_renewal
    renewal = threading.Thread(target=tick, args=(service, now, 4))
    response = threading.Thread(target=reply)
    renewal.start()
    try:
        assert entered.wait(2)
        response.start()
        assert replied.wait(1), "Other chats must not wait for typing network calls"
        assert 4 not in service.leases
    finally:
        release.set()
        renewal.join(2)
        if response.ident is not None:
            response.join(2)
    assert not service.chat_locks


def test_busy_chat_is_retried_then_expired(typing):
    service, client, now = typing
    service.start(3, 5)
    client.call.reset_mock()
    waiting = threading.Event()

    now[0] = 4

    def renew():
        waiting.set()
        service._tick()

    with service._chat_lock(3):
        worker = threading.Thread(target=renew)
        worker.start()
        assert waiting.wait(2)
        worker.join(2)
        assert not worker.is_alive()
        assert service.leases[3] == (5, 4.25)
        now[0] = 6
        expiry = threading.Thread(target=service._tick)
        expiry.start()
        expiry.join(2)
        assert not expiry.is_alive()
    client.call.assert_not_called()
    assert not service.leases


def test_slow_reply_does_not_block_other_chat_renewals(typing):
    service, client, now = typing
    service.start(3, 30)
    service.start(4, 30)
    client.call.reset_mock()
    entered, release, finished = threading.Event(), threading.Event(), threading.Event()

    def slow_send(request):
        entered.set()
        release.wait(2)

    response = threading.Thread(
        target=service.send_message,
        args=(SendInput(chat_id=3, text="Hi"), slow_send),
    )

    def renew():
        tick(service, now, 4)
        finished.set()

    worker = threading.Thread(target=renew)
    response.start()
    try:
        assert entered.wait(2)
        worker.start()
        assert finished.wait(1), "Scheduler must skip a chat with an in-flight reply"
        client.call.assert_called_once_with(
            "sendChatAction", {"chat_id": 4, "action": "typing"}
        )
        assert service.leases[3] == (30, 4.25)
        assert service.leases[4] == (30, 8)
    finally:
        release.set()
        response.join(2)
        if worker.ident is not None:
            worker.join(2)
    assert not response.is_alive() and not worker.is_alive()
    assert 3 not in service.leases
    assert not service.chat_locks


def test_busy_chat_renews_after_failed_reply(typing):
    service, client, now = typing
    service.start(3, 30)
    client.call.reset_mock()
    attempted = threading.Event()

    def send(request):
        worker = threading.Thread(target=lambda: (tick(service, now, 4), attempted.set()))
        worker.start()
        assert attempted.wait(1)
        worker.join(2)
        raise RuntimeError("send failed")

    with pytest.raises(RuntimeError):
        service.send_message(SendInput(chat_id=3, text="Hi"), send)
    tick(service, now, 4.24)
    client.call.assert_not_called()
    tick(service, now, 4.25)
    client.call.assert_called_once_with("sendChatAction", {"chat_id": 3, "action": "typing"})


def test_real_worker_wakes_for_new_lease(monkeypatch):
    now = [0.0]
    waiting = threading.Event()
    client = Mock()
    service = TypingService(client, clock=lambda: now[0], chance=lambda: 0.1)
    original_wait = service.condition.wait
    waits = []

    def observed_wait(timeout=None):
        waits.append(timeout)
        waiting.set()
        return original_wait(timeout)

    monkeypatch.setattr(service.condition, "wait", observed_wait)
    try:
        service.start(3, 30)
        assert waiting.wait(2)
        # Synchronize with the worker entering its real condition wait.
        with service.condition:
            service.clear()
            waiting.clear()
        assert waiting.wait(2)
        with service.condition:
            assert waits[-1] is None  # Idle worker, no polling deadline.
            waiting.clear()
        service.start(4, 30)  # Must wake that idle worker.
        assert waiting.wait(2)
        with service.condition:
            assert waits[-1] == 4
    finally:
        service.close()
    assert not service.thread.is_alive()


def test_real_worker_renews_on_timer_without_notifications():
    renewed = threading.Event()
    client = Mock()
    service = TypingService(client, chance=lambda: 0.1)
    calls = []

    def provider(method, payload):
        calls.append((method, payload))
        if len(calls) >= 2:
            renewed.set()

    client.call.side_effect = provider
    try:
        service.start(3, 30)
        # No clock override, manual tick or notification: only the real timer
        # can trigger the renewal after the initial synchronous API call.
        assert renewed.wait(6), "Worker did not renew when its timer expired"
        assert calls[:2] == [
            ("sendChatAction", {"chat_id": 3, "action": "typing"}),
            ("sendChatAction", {"chat_id": 3, "action": "typing"}),
        ]
    finally:
        service.close()
    assert not service.thread.is_alive()
