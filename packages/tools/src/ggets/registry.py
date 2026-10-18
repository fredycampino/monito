"""Explicit build-time tool registration."""

from ggets.health.module import create_module
from ggets.telegram.module import create_module as create_telegram_module

MODULES = {
    "health": (create_module, ("check", "info")),
    "telegram": (create_telegram_module, ("start", "stop", "status", "send")),
}
