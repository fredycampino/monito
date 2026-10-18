"""CLI transport. Module commands own their JSON input contracts."""

import argparse
import json

from ggets.config import load_config
from ggets.registry import MODULES
from ggets.tool_manager import ToolManager


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("Invalid command or arguments")


def main(argv=None, *, registry=None):
    try:
        config = load_config()
        manager = ToolManager(MODULES if registry is None else registry, config)
        parser = Parser(prog="ggets")
        commands = parser.add_subparsers(dest="command", required=True)
        commands.add_parser("serve", help="Run the HTTP server")
        manager.register_cli(commands)
        args = parser.parse_args(argv)
        if args.command == "serve":
            import uvicorn
            from ggets.server import ServerConfig, create_app

            server = ServerConfig.load(config.get("server", {}))
            uvicorn.run(create_app(manager, server), host=server.host, port=server.port)
        else:
            with manager.lifespan():
                print(json.dumps(args.execute(args)))
        return 0
    except ValueError as exc:
        print(json.dumps({"error": {"code": "invalid_input", "message": str(exc)}}))
        return 2
    except Exception:
        print(json.dumps({"error": {"code": "internal_error"}}))
        return 1
