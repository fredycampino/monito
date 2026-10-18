"""Include the shared webhook flow from a checkout or an extracted sdist."""

from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        source = root / "webhook/webhook.yaml"
        if not source.is_file():
            source = root.parent / "webhook/webhook.yaml"
        if not source.is_file():
            raise FileNotFoundError("Shared webhook flow is missing")
        build_data["force_include"][str(source)] = "packages/webhook/webhook.yaml"
