from ipaddress import IPv4Address

from pydantic import HttpUrl, IPvAnyAddress, PositiveInt

from callbot.auth.algorithm import Algorithm, DEFAULT_ALGORITHM
from callbot.settings._section import SettingsSection


class AuthSettings(SettingsSection):
    secret: str = "secret"
    alg: Algorithm = DEFAULT_ALGORITHM
    iss: str | None = None
    aud: str | None = None
    expiration_seconds: int = 15 * 60


class ServerSettings(SettingsSection):
    host: IPvAnyAddress = IPv4Address("127.0.0.1")
    port: PositiveInt = 8000
    public_base_url: HttpUrl | None = None
    auth: AuthSettings = AuthSettings()
