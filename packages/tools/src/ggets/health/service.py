import platform

from ggets.health.schemas import CheckOutput, InfoOutput


class HealthService:
    def __init__(self, config):
        self.config = config

    def check(self, request):
        return CheckOutput(status="ok", label=self.config.label)

    def info(self, request):
        return InfoOutput(
            python_version=platform.python_version(),
            operating_system=platform.system(),
            architecture=platform.machine(),
        )
