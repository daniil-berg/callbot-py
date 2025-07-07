from logging import INFO

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import IntLogLevel, LogModules


class LoggingSettings(SettingsSection):
    level: IntLogLevel = INFO
    format: str = "<level>{level: <8}</level> | <level>{message}</level> | <cyan>{name}</cyan>"
    modules: LogModules = {
        "aiosqlite": False,
        "sqlalchemy": False,
        "websockets": False,
    }
