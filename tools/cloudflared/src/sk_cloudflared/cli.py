import argparse

from sk_cloudflared.login import LoginService
from sk_cloudflared.tunnel import TunnelService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cloudflared tunnel management for Monito")
    commands = parser.add_subparsers(dest="command", required=True)
    login = commands.add_parser("login", help="Manage the human-assisted Cloudflare login")
    login_commands = login.add_subparsers(dest="login_command", required=True)
    for command in ("start", "status", "stop"):
        login_commands.add_parser(command)

    tunnel = commands.add_parser("tunnel", help="Manage named local tunnel connectors")
    tunnel_commands = tunnel.add_subparsers(dest="tunnel_command", required=True)
    registered = tunnel_commands.add_parser(
        "register", help="Register a user-provided Cloudflared YAML path"
    )
    registered.add_argument("--name", required=True)
    registered.add_argument("--config", required=True)
    tunnel_commands.add_parser("list", help="List remote Cloudflare tunnels")
    for command in ("open", "status", "close"):
        named = tunnel_commands.add_parser(command)
        named.add_argument("--name", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "login":
        result = getattr(LoginService(), args.login_command)()
    else:
        service = TunnelService()
        if args.tunnel_command == "register":
            result = service.register(args.name, args.config)
        elif args.tunnel_command == "list":
            result = service.list()
        else:
            result = getattr(service, args.tunnel_command)(args.name)
    print(result.as_json())
    if not result.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
