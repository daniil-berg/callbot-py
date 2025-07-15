from pydantic import PositiveInt, SecretStr

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import (
    SecretStrNoneAsEmpty,
    StrNoneAsEmpty,
    StrPhone,
)


class TwilioSettings(SettingsSection):
    account_sid: StrNoneAsEmpty = ""
    auth_token: SecretStrNoneAsEmpty = SecretStr("")
    phone_number: StrPhone | None = None
    timeout: PositiveInt = 60
