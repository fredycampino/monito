"""Provider listener owned by Telegram, not the tools API."""

import socket
import threading
import time
from contextlib import contextmanager

import uvicorn
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse


def create_receiver(service):
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.post(service.config.webhook)
    def receive(update: dict, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
        try:
            return service.receive_update(update, x_telegram_bot_api_secret_token)
        except PermissionError:
            return JSONResponse({"error": {"code": "unauthorized"}}, status_code=401)
        except ValueError:
            return JSONResponse({"error": {"code": "invalid_input"}}, status_code=422)
        except Exception:
            return JSONResponse({"error": {"code": "delivery_failed"}}, status_code=503)

    return app


@contextmanager
def receiver_lifespan(service):
    config = service.config
    if not all((config.base_url, config.bot_father_token_file, config.webhook_secret_file)):
        yield
        return
    service.secret()
    sock = socket.create_server((config.receiver_host, config.receiver_port))
    server = uvicorn.Server(
        uvicorn.Config(
            create_receiver(service),
            log_level="warning",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    try:
        thread.start()
        deadline = time.monotonic() + 5
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("Telegram receiver failed to start")
            time.sleep(0.01)
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=config.request_timeout_seconds + 5)
        sock.close()
