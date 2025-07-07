from pydantic import ConfigDict

from callbot.settings._section import SettingsSection


class PluginsSettings(SettingsSection):
    model_config = ConfigDict(extra="allow")
