import pytest
from ggets.health.config import DEFAULT_CONFIG, Config, map_config


def test_missing_values_use_defaults():
    result = map_config({})
    assert result == DEFAULT_CONFIG
    assert result is not DEFAULT_CONFIG


def test_valid_value_overrides_default():
    assert map_config({"label": "local"}) == Config(label="local")
    assert DEFAULT_CONFIG.label == "tools"


@pytest.mark.parametrize("label", [None, "", "  ", 4, True, [], {}])
def test_invalid_values_keep_default(label):
    assert map_config({"label": label}) == DEFAULT_CONFIG


def test_unknown_fields_are_ignored():
    assert map_config({"label": "local", "unknown": 1}) == Config(label="local")


def test_input_is_not_modified():
    value = {"label": "local"}
    map_config(value)
    assert value == {"label": "local"}
