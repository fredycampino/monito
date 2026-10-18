"""JSON command adapters for the consumer operations."""

from ggets.telegram.help import describe_operations
from ggets.telegram.schemas import EmptyInput, SendInput, StartInput
from pydantic import ValidationError


def register_cli(parser, service, enabled_operations):
    operations = parser.add_subparsers(dest="operation", required=True)

    def validate(schema, args):
        try:
            return schema.model_validate_json(args.json)
        except ValidationError:
            raise ValueError("Invalid telegram input") from None

    def execute_start(args):
        return service.start(validate(StartInput, args)).model_dump()

    def execute_stop(args):
        return service.stop(validate(EmptyInput, args)).model_dump()

    def execute_status(args):
        return service.status(validate(EmptyInput, args)).model_dump()

    def execute_send(args):
        return service.send(validate(SendInput, args)).model_dump()

    def execute_help(args):
        return describe_operations(enabled_operations)

    help_command = operations.add_parser("help")
    help_command.set_defaults(execute=execute_help)
    handlers = {
        "start": execute_start,
        "stop": execute_stop,
        "status": execute_status,
        "send": execute_send,
    }
    for name in enabled_operations:
        command = operations.add_parser(name)
        command.add_argument("--json", default="{}", help="JSON input object")
        command.set_defaults(execute=handlers[name])
