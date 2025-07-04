import asyncio
# TODO: Replace `argparse` with `typer`.
from argparse import ArgumentParser, Namespace
from pathlib import Path

import uvicorn

from callbot.contacts import import_contacts
from callbot.misc.logging import configure_logging
from callbot.server import app
from callbot.settings import Settings


def serve(args: Namespace) -> None:
    settings = Settings()
    if args.host is not None:
        settings.server.host = args.host
    if args.port is not None:
        settings.server.port = args.port
    uvicorn.run(
        app,
        host=str(settings.server.host),
        port=settings.server.port,
        log_config=None,
        log_level=None,
    )


def contacts(args: Namespace) -> None:
    if args.contacts_cmd == "import":
        asyncio.run(import_contacts(args.path))
        return
    raise RuntimeError(f"{args=}")


def main() -> None:
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_serve = subparsers.add_parser("serve")
    parser_serve.add_argument(
        "-H", "--host",
        help="Host/IP address to listen on",
    )
    parser_serve.add_argument(
        "-P", "--port",
        type=int,
        help="Port to listen on",
    )
    parser_serve.set_defaults(cmd=serve)

    parser_contacts = subparsers.add_parser("contacts")
    subparsers_contacts = parser_contacts.add_subparsers(dest="contacts_cmd")
    parser_contacts_import = subparsers_contacts.add_parser("import")
    parser_contacts_import.add_argument(
        "path",
        type=Path,
    )
    parser_contacts.set_defaults(cmd=contacts)
    configure_logging()
    args = parser.parse_args()
    args.cmd(args)


if __name__ == "__main__":
    main()
