from typing import Literal

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import Float1orGreater


class MiscSettings(SettingsSection):
    default_phone_region: str | None = None
    mode: Literal["testing", "production"] = "testing"
    speech_start_timeout: Float1orGreater | None = 10.
