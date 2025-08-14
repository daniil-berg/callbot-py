from pydantic import PositiveInt, SecretStr

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import (
    SecretStrNoneAsEmpty,
    StrPhone,
    TwilioAccountSID,
)


class TwilioSettings(SettingsSection):
    account_sid: TwilioAccountSID | None = None
    auth_token: SecretStrNoneAsEmpty = SecretStr("")
    phone_number: StrPhone | None = None
    timeout: PositiveInt = 60
