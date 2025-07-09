from importlib import import_module
from importlib.metadata import entry_points
from typing import Annotated

import uvicorn
from loguru import logger as log
from typer import Option, Typer

from callbot.functions import Function
from callbot.settings import Settings


app = Typer()


@app.command()
def serve(
    host: Annotated[
        str | None,
        Option(
            "-H", "--host",
            help="Host/IP address to listen on",
        ),
    ] = None,
    port: Annotated[
        int | None,
        Option(
            "-P", "--port",
            help="Port to listen on",
        ),
    ] = None,
) -> None:
    from callbot import server

    settings = Settings()
    if host is not None:
        settings.server.host = host  # type: ignore[assignment]
    if port is not None:
        settings.server.port = port
    log.info("Starting callbot server...")
    import_module("callbot.functions")
    for plugin in entry_points(group="callbot.functions"):
        plugin.load()
    functions = sorted(Function.registry.keys())
    log.debug(f"Available callbot functions: {functions}")
    uvicorn.run(
        server.app,
        host=str(settings.server.host),
        port=settings.server.port,
        log_config=None,
        log_level=None,
    )


serve_command = app.registered_commands[0]
