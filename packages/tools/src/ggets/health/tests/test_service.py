from unittest.mock import patch

from ggets.health.config import DEFAULT_CONFIG, Config
from ggets.health.schemas import CheckInput, InfoInput
from ggets.health.service import HealthService


def test_check_uses_default_configuration():
    result = HealthService(DEFAULT_CONFIG).check(CheckInput())
    assert result.status == "ok"
    assert result.label == DEFAULT_CONFIG.label


def test_check_uses_configured_label():
    result = HealthService(Config(label="local")).check(CheckInput())
    assert result.label == "local"


def test_info_reports_runtime_metadata():
    with (
        patch("ggets.health.service.platform.python_version", return_value="3.12.3"),
        patch("ggets.health.service.platform.system", return_value="Linux"),
        patch("ggets.health.service.platform.machine", return_value="aarch64"),
    ):
        result = HealthService(DEFAULT_CONFIG).info(InfoInput())
    assert result.python_version == "3.12.3"
    assert result.operating_system == "Linux"
    assert result.architecture == "aarch64"
