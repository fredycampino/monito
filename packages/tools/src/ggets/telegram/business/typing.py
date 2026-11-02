"""Process-local typing leases owned by the HTTP service."""

import logging
import random
import threading
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TypingService:
    def __init__(self, client, *, clock=time.monotonic, chance=random.random):
        self.client = client
        self.clock = clock
        self.chance = chance
        self.condition = threading.Condition(threading.RLock())
        self.leases = {}
        self.chat_locks = {}
        self.generation = 0
        self.thread = None
        self.closed = False

    def _send(self, chat_id):
        self.client.call("sendChatAction", {"chat_id": chat_id, "action": "typing"})

    @contextmanager
    def _chat_lock(self, chat_id, *, blocking=True):
        with self.condition:
            lock, users = self.chat_locks.get(chat_id, (threading.RLock(), 0))
            self.chat_locks[chat_id] = (lock, users + 1)
        acquired = lock.acquire(blocking=blocking)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()
            with self.condition:
                _, users = self.chat_locks[chat_id]
                if users == 1:
                    del self.chat_locks[chat_id]
                else:
                    self.chat_locks[chat_id] = (lock, users - 1)

    def start(self, chat_id, timeout):
        with self._chat_lock(chat_id):
            with self.condition:
                if self.closed:
                    raise RuntimeError("Typing service is stopped")
                generation = self.generation
            self._send(chat_id)
            with self.condition:
                if self.closed or generation != self.generation:
                    return
                now = self.clock()
                self.leases[chat_id] = (now + timeout, now + 4)
                if self.thread is None:
                    self.thread = threading.Thread(target=self._run, daemon=True)
                    self.thread.start()
                self.condition.notify_all()

    def send_message(self, request, send):
        # Only the same chat waits for an in-flight renewal before replying.
        with self._chat_lock(request.chat_id):
            result = send(request)
            with self.condition:
                self.leases.pop(request.chat_id, None)
                self.condition.notify_all()
            return result

    def clear(self):
        with self.condition:
            self.generation += 1
            self.leases.clear()
            self.condition.notify_all()

    def _tick(self):
        with self.condition:
            chats = list(self.leases)
        for chat_id in chats:
            with self._chat_lock(chat_id, blocking=False) as acquired:
                if not acquired:
                    with self.condition:
                        lease = self.leases.get(chat_id)
                        if lease is not None:
                            deadline, renewal = lease
                            now = self.clock()
                            if now >= deadline:
                                self.leases.pop(chat_id)
                            elif now >= renewal:
                                self.leases[chat_id] = (deadline, now + 0.25)
                    continue
                with self.condition:
                    lease = self.leases.get(chat_id)
                    if self.closed or lease is None:
                        continue
                    deadline, renewal = lease
                    now = self.clock()
                    if now >= deadline:
                        self.leases.pop(chat_id)
                        continue
                    if now < renewal:
                        continue
                    self.leases[chat_id] = (deadline, now + 4)
                    renew = self.chance() < 0.7
                if renew:
                    try:
                        self._send(chat_id)
                    except Exception:
                        logger.warning("Telegram typing renewal failed")

    def _run(self):
        while True:
            self._tick()
            with self.condition:
                if self.closed:
                    return
                wakeups = [min(deadline, renewal) for deadline, renewal in self.leases.values()]
                delay = max(0, min(wakeups) - self.clock()) if wakeups else None
                self.condition.wait(timeout=delay)

    def close(self):
        with self.condition:
            self.closed = True
            self.generation += 1
            self.leases.clear()
            self.condition.notify_all()
        if self.thread is not None:
            self.thread.join()
