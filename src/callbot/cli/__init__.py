import logging
from typing import Annotated

from typer import Exit, Option, Typer

from .serve import serve_command
from .contacts import app as contacts_app
from callbot.misc.logging import configure_logging
from callbot.settings import Settings


app = Typer(add_completion=False)
app.registered_commands.append(serve_command)
app.add_typer(contacts_app, name="contacts")


@app.callback()
def root(
    verbose: Annotated[
        int,
        Option(
            "--verbose", "-v",
            count=True,
            help="Increases log verbosity. Can be used multiple times. "
                 "One flag corresponds to the `INFO` log level. "
                 "Two or more correspond to the `DEBUG` log level. "
                 "If set, this will take precedence over the `level` setting "
                 "in the `logging` config section. "
                 "Can not be used together with the `--quiet` option.",
            show_default=False,
        ),
    ] = 0,
    quiet: Annotated[
        int,
        Option(
            "--quiet", "-q",
            count=True,
            help="Decreases log verbosity. Can be used multiple times. "
                 "One flag corresponds to the `ERROR` log level, "
                 "two correspond to the `CRITICAL` log level. "
                 "If set, this will take precedence over the `level` setting "
                 "in the `logging` config section. "
                 "Can not be used together with the `--verbose` option.",
            show_default=False,
        ),
    ] = 0,
) -> None:
    if verbose and quiet:
        print("Cannot use `--verbose` and `--quiet` together.")
        raise Exit(code=1)
    settings = Settings()
    if verbose == 1:
        settings.logging.level = logging.INFO
    elif verbose >= 2:
        settings.logging.level = logging.DEBUG
    if quiet == 1:
        settings.logging.level = logging.ERROR
    elif quiet >= 2:
        settings.logging.level = logging.CRITICAL
    configure_logging()
