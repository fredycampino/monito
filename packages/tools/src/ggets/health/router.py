from fastapi import APIRouter
from ggets.health.schemas import CheckInput, CheckOutput, InfoInput, InfoOutput


def create_router(service, enabled_operations):
    router = APIRouter(tags=["health"])

    def check(request: CheckInput):
        return service.check(request)

    def info(request: InfoInput):
        return service.info(request)

    endpoints = {
        "check": (check, CheckOutput),
        "info": (info, InfoOutput),
    }
    descriptions = {
        "check": "Check availability and instance label.",
        "info": "Get Python version, OS, and architecture.",
    }

    @router.get("/help")
    def help_operations():
        return {
            name: {
                "description": descriptions[name],
                "request": {
                    "method": "POST",
                    "path": f"/health/{name}",
                    "body": {},
                },
            }
            for name in enabled_operations
        }

    for name in enabled_operations:
        endpoint, response_model = endpoints[name]
        router.add_api_route(
            f"/{name}", endpoint, methods=["POST"], response_model=response_model
        )
    return router
