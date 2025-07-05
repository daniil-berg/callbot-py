import asyncio
from pathlib import Path
from typing import Annotated

from pydantic import ValidationError
from typer import Argument, BadParameter, Exit, Typer

from callbot.caller import Caller
from callbot.contacts import import_contacts
from callbot.schemas.contact import Phone


app = Typer()


@app.command("import")
def import_(
    path: Annotated[
        Path,
        Argument(help="Path to source CSV file"),
    ]
) -> None:
    asyncio.run(import_contacts(path))


@app.command()
def call(
    phone: Annotated[
        Phone,
        Argument(help="Phone number to issue the call to"),
    ],
) -> None:
    caller = Caller(pool=False)
    try:
        sid = asyncio.run(caller.get_contact_and_call(phone))
    except ValidationError as validation_error:
        raise BadParameter(validation_error.errors()[0]["msg"]) from None
    except Exception as exception:
        print(exception)
        raise Exit(1) from None
    print(f"Call SID for {phone}: {sid}")
