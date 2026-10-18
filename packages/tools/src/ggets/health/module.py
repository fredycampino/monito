from contextlib import nullcontext

from ggets.health.cli import register_cli
from ggets.health.config import map_config
from ggets.health.router import create_router
from ggets.health.service import HealthService


class HealthModule:
    def __init__(self, config, operations):
        if set(operations) - {"check", "info"}:
            raise ValueError("Unknown health operation")
        self.operations = tuple(operations)
        self.service = HealthService(map_config(config))
        self.router = create_router(self.service, self.operations)

    def register_cli(self, parser):
        register_cli(parser, self.service, self.operations)

    def lifespan(self):
        return nullcontext()


def create_module(config, operations):
    return HealthModule(config, operations)
