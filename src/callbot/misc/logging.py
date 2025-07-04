import inspect
import logging
import sys

from loguru import logger

from callbot.settings import Settings


DEPENDENCIES_LOGGERS = (
    "aiosqlite",
    "fastapi",
    "sqlalchemy",
    "starlette",
    "uvicorn",
)


class InterceptHandler(logging.Handler):
    """
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    settings = Settings()
    # Disable stdlib logging handlers for root logger and unset level.
    logging.root.handlers = []
    logging.root.setLevel(logging.NOTSET)
    # Intercept loggers of known dependencies and unset their levels.
    for name in DEPENDENCIES_LOGGERS:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [InterceptHandler()]
        std_logger.setLevel(logging.NOTSET)
    # Configure global log level and format.
    std_handler = {
        "sink": sys.stderr,
        "level": settings.logging.level,
        "format": settings.logging.format,
    }
    logger.configure(
        handlers=[std_handler],
        activation=list(settings.logging.modules.items()),
    )
