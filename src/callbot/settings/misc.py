from typing import Literal

from callbot.settings._section import SettingsSection


class MiscSettings(SettingsSection):
    default_phone_region: str | None = None
    mode: Literal["testing", "production"] = "testing"
