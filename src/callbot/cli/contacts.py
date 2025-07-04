import asyncio
from pathlib import Path
from typing import Annotated

from typer import Argument, Typer

from callbot.contacts import import_contacts


app = Typer()


@app.command("import")
def import_(
    path: Annotated[
        Path,
        Argument(help="Path to source CSV file"),
    ]
) -> None:
    asyncio.run(import_contacts(path))
