"""Consumer subscription lifecycle, independent of storage technology."""

from pydantic import HttpUrl, TypeAdapter, ValidationError


class ConsumerSubscriptionService:
    def __init__(self, store):
        self.store = store

    def activate(self, url):
        try:
            parsed = TypeAdapter(HttpUrl).validate_python(url)
        except ValidationError:
            raise ValueError("Invalid consumer URL") from None
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Invalid consumer URL")
        self.store.save({"url": str(parsed), "active": True})

    def deactivate(self):
        state = self.status()
        self.store.save({"url": state["url"], "active": False})

    def status(self):
        state = self.store.load()
        if state is None:
            return {"url": None, "active": False}
        if (
            not isinstance(state, dict)
            or type(state.get("active")) is not bool
            or not isinstance(state.get("url"), (str, type(None)))
            or (state["active"] and not state.get("url"))
        ):
            raise ValueError("Invalid subscription state")
        return {"url": state.get("url"), "active": state["active"]}
