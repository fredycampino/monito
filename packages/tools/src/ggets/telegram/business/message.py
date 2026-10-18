"""Outbound text messages."""


class MessageService:
    def __init__(self, client):
        self.client = client

    def send(self, request):
        result = self.client.call("sendMessage", request.model_dump())
        return {"chat_id": result["chat"]["id"], "message_id": result["message_id"]}
