from ggets.health.schemas import CheckInput, InfoInput
from pydantic import ValidationError


def register_cli(parser, service, enabled_operations):
    operations = parser.add_subparsers(dest="operation", required=True)
    def execute_check(args):
        try:
            request = CheckInput.model_validate_json(args.json)
        except ValidationError:
            raise ValueError("Invalid health input") from None
        return service.check(request).model_dump()

    def execute_info(args):
        try:
            request = InfoInput.model_validate_json(args.json)
        except ValidationError:
            raise ValueError("Invalid health input") from None
        return service.info(request).model_dump()

    handlers = {"check": execute_check, "info": execute_info}
    for name in enabled_operations:
        command = operations.add_parser(name)
        command.add_argument("--json", default="{}", help="JSON input object")
        command.set_defaults(execute=handlers[name])
