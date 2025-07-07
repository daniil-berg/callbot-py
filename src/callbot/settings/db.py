from sqlalchemy import URL

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import DBURLQuery


# TODO: Narrow field types.
class DBSettings(SettingsSection):
    driver: str = "sqlite+aiosqlite"
    username: str | None = None
    password: str | None = None
    host: str | None = None
    port: int | None = None
    name: str | None = None
    query: DBURLQuery = {}

    @property
    def url(self) -> URL:
        return URL.create(
            drivername=self.driver,
            username=self.username,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.name,
            query=self.query,
        )
