from unittest.mock import Mock

import pytest
from ggets.telegram.business.delivery import DeliveryError, DeliveryService
from ggets.telegram.business.incoming_update import IncomingUpdateService
from ggets.telegram.business.message import MessageService
from ggets.telegram.business.subscription import ConsumerSubscriptionService
from ggets.telegram.business.webhook import TelegramWebhookService
from ggets.telegram.schemas import SendInput


def test_webhook_lifecycle():
    client = Mock()
    service = TelegramWebhookService(client, "https://bot.example/telegram/webhook", "secret")
    service.register()
    assert client.call.call_args.args[0] == "setWebhook"
    assert client.call.call_args.args[1]["secret_token"] == "secret"
    assert client.call.call_args.args[1]["drop_pending_updates"] is False
    service.unregister()
    client.call.assert_called_with("deleteWebhook", {"drop_pending_updates": False})
    client.call.return_value = {"url": service.webhook_url, "pending_update_count": 2}
    assert service.status() == {"registered": True, "pending_updates": 2, "last_error_at": None}


def test_subscription():
    store = Mock()
    store.load.return_value = None
    service = ConsumerSubscriptionService(store)
    assert service.status() == {"url": None, "active": False}
    service.activate("https://consumer.example/inbox")
    store.save.assert_called_with({"url": "https://consumer.example/inbox", "active": True})
    store.load.return_value = store.save.call_args.args[0]
    service.deactivate()
    store.save.assert_called_with({"url": "https://consumer.example/inbox", "active": False})


@pytest.mark.parametrize("url", ["bad", "file:///tmp/x", "https://user:pass@example.com"])
def test_invalid_subscription(url):
    store = Mock()
    with pytest.raises(ValueError):
        ConsumerSubscriptionService(store).activate(url)
    store.save.assert_not_called()


def test_corrupt_state():
    store = Mock()
    store.load.return_value = {"active": True, "url": None}
    with pytest.raises(ValueError):
        ConsumerSubscriptionService(store).status()


def test_send():
    client = Mock()
    client.call.return_value = {"chat": {"id": 3}, "message_id": 7, "extra": "discard"}
    assert MessageService(client).send(SendInput(chat_id=3, text="Hi")) == {
        "chat_id": 3,
        "message_id": 7,
    }
    client.call.assert_called_with("sendMessage", {"chat_id": 3, "text": "Hi"})


def test_normalization():
    service = IncomingUpdateService("secret")
    event = service.process(
        {
            "update_id": 1,
            "message": {
                "chat": {"id": 3},
                "message_id": 7,
                "text": "Hi",
                "from": {"id": 4, "first_name": "A"},
            },
        },
        "secret",
    )
    assert event == {
        "event_id": "1",
        "type": "message",
        "chat_id": 3,
        "message_id": 7,
        "sender": {"id": 4, "name": "A"},
        "text": "Hi",
    }
    assert service.process({"update_id": 2}, "secret") is None
    with pytest.raises(ValueError):
        service.process({"update_id": 1, "message": {"text": "Hi"}}, "secret")


@pytest.mark.parametrize("secret", [None, "", "wrong"])
def test_reject_unauthenticated(secret):
    with pytest.raises(PermissionError):
        IncomingUpdateService("secret").process({}, secret)


@pytest.mark.parametrize("status", [200, 204, 302, 400, 500])
def test_delivery(status):
    transport = Mock()
    transport.post.return_value.status_code = status
    service = DeliveryService(transport, 10)
    if status < 300:
        service.deliver("https://consumer.example", {"event_id": "1"})
    else:
        with pytest.raises(DeliveryError):
            service.deliver("https://consumer.example", {"event_id": "1"})
    assert transport.post.call_args.kwargs["follow_redirects"] is False


def test_delivery_transport_failure_is_sanitized():
    transport = Mock()
    transport.post.side_effect = OSError("sensitive details")
    with pytest.raises(DeliveryError, match="^Consumer delivery failed$"):
        DeliveryService(transport, 10).deliver("https://consumer.example", {})
