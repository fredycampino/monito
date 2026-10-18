"""Telegram module assembly and lifecycle."""

from ggets.telegram.cli import register_cli
from ggets.telegram.config import map_config
from ggets.telegram.help import OPERATIONS
from ggets.telegram.receiver import receiver_lifespan
from ggets.telegram.router import create_router
from ggets.telegram.service import TelegramService


class TelegramModule:
    def __init__(self, config, operations):
        if set(operations) - set(OPERATIONS):
            raise ValueError("Unknown telegram operation")
        self.operations = tuple(operations)
        self.service = TelegramService(map_config(config))
        self.router = create_router(self.service, self.operations)

    def register_cli(self, parser):
        register_cli(parser, self.service, self.operations)

    def lifespan(self):
        return receiver_lifespan(self.service)


def create_module(config, operations):
    return TelegramModule(config, operations)
