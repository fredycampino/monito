"""Consumer delivery with explicit failure propagation."""


class DeliveryError(Exception):
    """Delivery was not confirmed; the caller must not acknowledge the update."""


class DeliveryService:
    def __init__(self, transport, timeout):
        self.transport = transport
        self.timeout = timeout

    def deliver(self, url, event):
        try:
            response = self.transport.post(
                url, json=event, timeout=self.timeout, follow_redirects=False
            )
        except Exception:
            raise DeliveryError("Consumer delivery failed") from None
        if not 200 <= response.status_code < 300:
            raise DeliveryError("Consumer delivery failed")
