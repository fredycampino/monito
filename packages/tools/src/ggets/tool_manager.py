"""Composition and lifecycle; no integration-specific behavior."""

from contextlib import ExitStack, contextmanager


class ToolManager:
    def __init__(self, registry, config):
        unknown = set(config) - set(registry) - {"server"}
        if unknown:
            raise ValueError("Unknown configuration section")
        self.modules = {}
        for name, (factory, operations) in registry.items():
            section = config.get(name, {})
            if not isinstance(section, dict):
                raise ValueError("Module configuration must be an object")
            self.modules[name] = factory(section, operations)

    @contextmanager
    def lifespan(self):
        with ExitStack() as stack:
            for module in self.modules.values():
                stack.enter_context(module.lifespan())
            yield self

    def register_cli(self, subparsers):
        for name, module in self.modules.items():
            module.register_cli(subparsers.add_parser(name))

    def register_http(self, app):
        for name, module in self.modules.items():
            app.include_router(module.router, prefix=f"/{name}")
