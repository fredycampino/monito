import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from ggets.cli import main
from ggets.config import load_config
from ggets.server import ServerConfig, create_app
from ggets.tool_manager import ToolManager


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("GGETS_CONFIG_FILE", raising=False)


def test_register_cli():
    module = Mock()
    subparsers = Mock()
    manager = ToolManager({"sample": (lambda config, operations: module, ("check",))}, {})
    manager.register_cli(subparsers)
    subparsers.add_parser.assert_called_once_with("sample")
    module.register_cli.assert_called_once_with(subparsers.add_parser.return_value)


def test_register_http():
    module = Mock()
    app = Mock()
    manager = ToolManager({"sample": (lambda config, operations: module, ("check",))}, {})
    manager.register_http(app)
    app.include_router.assert_called_once_with(module.router, prefix="/sample")


def test_config(monkeypatch, tmp_path):
    assert load_config() == {}
    path = tmp_path / "config.json"
    monkeypatch.setenv("GGETS_CONFIG_FILE", str(path))
    with pytest.raises(ValueError):
        load_config()
    path.write_text('{"sample": {"setting": "local"}}')
    assert load_config()["sample"] == {"setting": "local"}
    path.write_text("[]")
    with pytest.raises(ValueError):
        load_config()


def test_auth(tmp_path):
    path = tmp_path / "token"
    path.write_text("private-value")
    config = ServerConfig.load({"token_file": str(path)})
    from contextlib import nullcontext

    manager = Mock()
    manager.lifespan.side_effect = nullcontext
    with TestClient(create_app(manager, config)) as client:
        response = client.get("/openapi.json")
        assert response.status_code == 401
        assert "private-value" not in response.text
        assert client.get("/openapi.json", headers={
            "Authorization": "Bearer private-value"}).status_code == 200


def test_errors(capsys):
    assert main(["missing"], registry={}) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "invalid_input"


@pytest.mark.parametrize("config", [{"port": 0}, {"port": True}, {"host": ""}])
def test_bad_server(config):
    with pytest.raises(ValueError):
        ServerConfig.load(config)


def test_lifecycle_closes_on_failure():
    from contextlib import contextmanager

    events = []

    class Module:
        @contextmanager
        def lifespan(self):
            events.append("start")
            try:
                yield
            finally:
                events.append("stop")

    def factory(config, operations):
        assert operations == ("check",)
        assert config == {"setting": 1}
        return Module()

    manager = ToolManager(
        {"sample": (factory, ("check",))}, {"sample": {"setting": 1}, "server": {}}
    )
    with pytest.raises(RuntimeError), manager.lifespan():
        raise RuntimeError("test")
    assert events == ["start", "stop"]


def test_unknown_section_rejected():
    with pytest.raises(ValueError):
        ToolManager({}, {"unknown": {}})


def test_factory_receives_only_registered_operations():
    factory = Mock()
    ToolManager({"sample": (factory, ("selected",))}, {"sample": {"setting": 1}})
    factory.assert_called_once_with({"setting": 1}, ("selected",))


def test_validation_error_matches_openapi():
    from contextlib import nullcontext

    from fastapi import APIRouter

    router = APIRouter()

    @router.post("/sample")
    def sample(value: int):
        return {"value": value}

    manager = Mock()
    manager.lifespan.side_effect = nullcontext
    manager.register_http.side_effect = lambda app: app.include_router(router)
    with TestClient(create_app(manager, ServerConfig())) as client:
        response = client.post("/sample", params={"value": "invalid"})
        assert response.status_code == 422
        assert response.json() == {"error": {"code": "invalid_input"}}
        schema = client.get("/openapi.json").json()
        documented = schema["paths"]["/sample"]["post"]["responses"]["422"]
        assert documented["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }


@pytest.mark.parametrize("command", ["health", "telegram"])
def test_cli_calls_service_without_module_lifespans(command, monkeypatch, capsys):
    from ggets.health.module import create_module as create_health
    from ggets.telegram.module import create_module as create_telegram

    modules = {
        "health": create_health({}, ("check",)),
        "telegram": create_telegram({}, ("send",)),
    }
    for module in modules.values():
        monkeypatch.setattr(module, "lifespan", Mock(side_effect=AssertionError("CLI lifecycle")))
    send = Mock()
    send.return_value.model_dump.return_value = {"status": "ok", "data": {"message_id": 1}}
    monkeypatch.setattr(modules["telegram"].service, "send", send)
    registry = {
        name: (lambda config, operations, module=module: module, ())
        for name, module in modules.items()
    }
    args = ["health", "check"] if command == "health" else [
        "telegram", "send", "--json", '{"chat_id": 123, "text": "test"}'
    ]

    assert main(args, registry=registry) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    for module in modules.values():
        module.lifespan.assert_not_called()
    if command == "telegram":
        send.assert_called_once()
        request = send.call_args.args[0]
        assert request.chat_id == 123
        assert request.text == "test"
    else:
        send.assert_not_called()


def test_http_application_starts_and_stops_all_module_lifespans():
    from contextlib import contextmanager

    from fastapi import APIRouter

    events = []

    def factory(name):
        module = Mock()
        module.router = APIRouter()

        @contextmanager
        def lifespan():
            events.append((name, "start"))
            try:
                yield
            finally:
                events.append((name, "stop"))

        module.lifespan.side_effect = lifespan
        return lambda config, operations: module

    manager = ToolManager({name: (factory(name), ()) for name in ("first", "second")}, {})
    app = create_app(manager, ServerConfig())
    assert events == []
    with TestClient(app) as client:
        assert events == [("first", "start"), ("second", "start")]
        assert client.get("/openapi.json").status_code == 200
    assert events == [
        ("first", "start"), ("second", "start"),
        ("second", "stop"), ("first", "stop"),
    ]
