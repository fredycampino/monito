"""Central HTTP transport and optional consumer authentication."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from hmac import compare_digest
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


@dataclass(frozen=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    token: str | None = None

    @classmethod
    def load(cls, value):
        if not isinstance(value, dict) or set(value) - {"host", "port", "token_file"}:
            raise ValueError("Invalid server configuration")
        host, port = value.get("host", "127.0.0.1"), value.get("port", 8000)
        if not isinstance(host, str) or not host:
            raise ValueError("Invalid server host")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid server port")
        token = None
        if "token_file" in value:
            try:
                token = Path(value["token_file"]).expanduser().read_text().strip()
            except (OSError, TypeError, ValueError):
                raise ValueError("Cannot read server token") from None
            if not token:
                raise ValueError("Empty server token")
        return cls(host, port, token)


def create_app(manager, config):
    @asynccontextmanager
    async def lifespan(app):
        with manager.lifespan():
            yield

    # Explicit 422 overrides FastAPI's default validation-error contract.
    responses = {
        422: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    }
    if config.token:
        responses[401] = {"model": ErrorResponse, "description": "Unauthorized"}
    app = FastAPI(title="Tools", lifespan=lifespan, responses=responses)

    @app.middleware("http")
    async def authenticate(request: Request, call_next):
        expected = f"Bearer {config.token}"
        actual = request.headers.get("authorization", "")
        if config.token and not compare_digest(actual.encode(), expected.encode()):
            return JSONResponse({"error": {"code": "unauthorized"}}, status_code=401)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"error": {"code": "invalid_input"}}, status_code=422)

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        return JSONResponse({"error": {"code": "internal_error"}}, status_code=500)

    manager.register_http(app)
    return app
