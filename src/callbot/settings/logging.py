from logging import INFO

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import IntLogLevel, LogModules


class LoggingSettings(SettingsSection):
    format: str = "<level>{level: <8}</level> | <level>{message}</level> | <cyan>{name}</cyan>"
    level: IntLogLevel = INFO
    modules: LogModules = {
        "aiosqlite": False,
        "sqlalchemy": False,
        "websockets": False,
    }
    transcript: bool = True
