from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from ggets.telegram.adapters import SubscriptionStore, TelegramClient
from ggets.telegram.config import map_config
from ggets.telegram.receiver import create_receiver, receiver_lifespan
from ggets.telegram.schemas import EmptyInput, StartInput
from ggets.telegram.service import TelegramService


@pytest.fixture
def service(tmp_path):
    secret = tmp_path / "secret"
    secret.write_text("test-secret")
    token = tmp_path / "bot-token"
    token.write_text("fake-token")
    config = map_config(
        {
            "base_url": "https://bot.example",
            "bot_father_token_file": str(token),
            "webhook_secret_file": str(secret),
            "state_file": str(tmp_path / "state.json"),
        }
    )
    client = Mock()
    transport = Mock()
    transport.post.return_value.status_code = 200
    return TelegramService(config, client=client, transport=transport)


def test_lifecycle_and_delivery(service):
    assert service.start(StartInput(url="https://consumer.example/inbox")).data["active"]
    service.client.call.return_value = {"url": service.config.webhook_url}
    assert service.status(EmptyInput()).data["webhook"]["registered"]
    receiver = TestClient(create_receiver(service))
    update = {"update_id": 1, "message": {"chat": {"id": 2}, "message_id": 3, "text": "Hi"}}
    assert receiver.post(service.config.webhook, json=update).status_code == 401
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
    assert receiver.post(service.config.webhook, json=update, headers=headers).status_code == 200
    service.delivery.transport.post.assert_called_once()
    service.delivery.transport.post.return_value.status_code = 500
    assert receiver.post(service.config.webhook, json=update, headers=headers).status_code == 503
    assert receiver.get("/openapi.json").status_code == 404
    assert not service.stop(EmptyInput()).data["active"]
    assert receiver.post(service.config.webhook, json=update, headers=headers).status_code == 503


def test_failed_start_restores_state(service):
    service.client.call.side_effect = RuntimeError("failure")
    with pytest.raises(RuntimeError):
        service.start(StartInput(url="https://consumer.example"))
    assert service.subscription.status() == {"url": None, "active": False}


def test_storage(tmp_path):
    store = SubscriptionStore(tmp_path / "nested/state.json")
    assert store.load() is None
    store.save({"url": "https://example.com", "active": True})
    assert store.load()["active"]
    assert store.path.stat().st_mode & 0o777 == 0o600


def test_provider_error_is_sanitized(service, monkeypatch):
    monkeypatch.setattr(
        "ggets.telegram.adapters.httpx.post", Mock(side_effect=RuntimeError("token"))
    )
    with pytest.raises(RuntimeError, match="^Telegram request failed$"):
        TelegramClient(service.config).call("getMe", {})


def test_unconfigured_listener_does_not_start():
    with receiver_lifespan(TelegramService(map_config({}))):
        pass


def test_tools_router_has_no_ingress(service):
    from fastapi import FastAPI
    from ggets.telegram.router import create_router

    app = FastAPI()
    app.include_router(create_router(service, ("status",)), prefix="/telegram")
    client = TestClient(app)
    assert client.post("/telegram/webhook", json={}).status_code == 404
    assert set(client.get("/openapi.json").json()["paths"]) == {
        "/telegram/status",
        "/telegram/help",
    }


@pytest.mark.parametrize("missing", ["base_url", "bot_father_token_file", "webhook_secret_file"])
def test_missing_configuration_http(service, missing):
    from dataclasses import replace

    from fastapi import FastAPI
    from ggets.telegram.router import create_router

    service.config = replace(service.config, **{missing: None})
    app = FastAPI()
    app.include_router(create_router(service, ("status", "start", "stop", "send")),
                       prefix="/telegram")
    client = TestClient(app)
    response = client.post("/telegram/status", json={})
    assert response.status_code == 200
    assert response.json() == {
        "status": "not_configured", "data": {"missing_fields": [missing]}
    }
    for operation, body in (
        ("start", {"url": "https://consumer.example/inbox"}),
        ("stop", {}),
        ("send", {"chat_id": 1, "text": "Hi"}),
    ):
        response = client.post("/telegram/" + operation, json=body)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "configuration_error"
    service.client.call.assert_not_called()
    assert service.subscription.status() == {"url": None, "active": False}
