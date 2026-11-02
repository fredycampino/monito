"""Consumer routes and a separate, undocumented provider ingress route."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ggets.telegram.config import ConfigurationError
from ggets.telegram.help import describe_operations
from ggets.telegram.schemas import EmptyInput, OperationResult, SendInput, StartInput, TypingInput


def create_router(service, enabled_operations):
    router = APIRouter(tags=["telegram"])

    @router.get("/help")
    def help_operations():
        return describe_operations(enabled_operations)

    def invoke(operation, request):
        try:
            return operation(request)
        except ConfigurationError as exc:
            return JSONResponse(
                {"error": {"code": "configuration_error", "message": str(exc)}},
                status_code=503,
            )

    def start(request: StartInput):
        return invoke(service.start, request)

    def stop(request: EmptyInput):
        return invoke(service.stop, request)

    def status(request: EmptyInput):
        return invoke(service.status, request)

    def send(request: SendInput):
        return invoke(service.send, request)

    def typing(request: TypingInput):
        try:
            return invoke(service.typing, request)
        except RuntimeError:
            return JSONResponse(
                {"error": {"code": "telegram_request_failed"}}, status_code=502
            )

    endpoints = {"start": start, "stop": stop, "status": status, "send": send, "typing": typing}
    for name in enabled_operations:
        router.add_api_route(
            f"/{name}",
            endpoints[name],
            methods=["POST"],
            response_model=OperationResult,
        )

    return router
