from dataclasses import asdict

import pytest
from ggets.telegram.config import DEFAULT_CONFIG, map_config


def test_defaults_are_independent():
    config = map_config({})
    assert config == DEFAULT_CONFIG
    assert config is not DEFAULT_CONFIG
    assert config.webhook == "/telegram/webhook"
    assert config.state_file == "/data/telegram/state.json"
    assert config.request_timeout_seconds == 10


def test_valid_configuration():
    values = {
        "base_url": "https://bot.example/",
        "webhook": "/telegram/incoming",
        "bot_father_token_file": "test-token-not-real",
        "webhook_secret_file": "/secrets/webhook",
        "state_file": "/state/telegram.json",
        "request_timeout_seconds": 25,
    }
    config = map_config(values)
    config.require_configured()
    assert config.webhook_url == "https://bot.example/telegram/incoming"
    assert asdict(config) == {**asdict(DEFAULT_CONFIG), **values, "base_url": "https://bot.example"}
    assert "test-token-not-real" not in repr(config)
    assert DEFAULT_CONFIG.base_url is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_url", "http://bot.example"),
        ("base_url", "https://user:password@bot.example"),
        ("base_url", "https://bot.example/path"),
        ("base_url", "https://bot.example:invalid"),
        ("base_url", "https://bot.example?q=1"),
        ("base_url", None),
        ("webhook", "/other/webhook"),
        ("webhook", "/telegram/start"),
        ("webhook", "/telegram/typing"),
        ("webhook", "/telegram/../start"),
        ("webhook", "/telegram/{path}"),
        ("webhook", "/telegram/hook?q=1"),
        ("bot_father_token_file", "  "),
        ("bot_father_token_file", 42),
        ("webhook_secret_file", False),
        ("state_file", ""),
        ("request_timeout_seconds", True),
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", -1),
        ("request_timeout_seconds", "10"),
    ],
)
def test_invalid_values_retain_defaults(field, value):
    assert getattr(map_config({field: value}), field) == getattr(DEFAULT_CONFIG, field)


def test_required_fields_report_names_only():
    with pytest.raises(ValueError) as error:
        map_config({"bot_father_token_file": "test-token-not-real"}).require_configured()
    assert str(error.value) == "Missing Telegram configuration: base_url, webhook_secret_file"
    assert "test-token-not-real" not in str(error.value)
    with pytest.raises(ValueError):
        _ = map_config({}).webhook_url


def test_unknown_fields_do_not_change_defaults():
    assert map_config({"consumer_url": "https://consumer.example"}) == DEFAULT_CONFIG


def test_mapper_does_not_read_secret_file(tmp_path):
    missing = tmp_path / "missing-secret"
    config = map_config({"webhook_secret_file": str(missing)})
    assert config.webhook_secret_file == str(missing)
    assert not missing.exists()
