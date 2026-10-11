import os

from sk_telegram.config import load_local_config, skiller_executable


def test_local_config_loads_non_exported_values(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text("SKILLER_BIN=/from/dotenv/skiller\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SKILLER_BIN", raising=False)

    load_local_config()

    assert skiller_executable() is None
    assert os.environ["SKILLER_BIN"] == "/from/dotenv/skiller"


def test_exported_value_has_priority_over_dotenv(monkeypatch, tmp_path) -> None:
    (tmp_path / ".env").write_text("SKILLER_BIN=/from/dotenv/skiller\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SKILLER_BIN", "/exported/skiller")

    load_local_config()

    assert os.environ["SKILLER_BIN"] == "/exported/skiller"


def test_skiller_executable_prefers_configured_binary(monkeypatch) -> None:
    monkeypatch.setenv("SKILLER_BIN", "/development/skiller")
    monkeypatch.setattr(
        "sk_telegram.config.shutil.which",
        lambda command: command if command == "/development/skiller" else None,
    )

    assert skiller_executable() == "/development/skiller"


def test_skiller_executable_falls_back_to_path(monkeypatch) -> None:
    monkeypatch.delenv("SKILLER_BIN", raising=False)
    monkeypatch.setattr(
        "sk_telegram.config.shutil.which",
        lambda command: "/usr/bin/skiller" if command == "skiller" else None,
    )

    assert skiller_executable() == "/usr/bin/skiller"
