from typing import Any, cast

import yaml
from pydantic._internal._model_construction import ModelMetaclass
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from callbot.misc.singleton import Singleton
from callbot.settings._section import SettingsSection
from callbot.settings.db import DBSettings
from callbot.settings.elevenlabs import ElevenlabsSettings
from callbot.settings.logging import LoggingSettings
from callbot.settings.misc import MiscSettings
from callbot.settings.openai import OpenAISettings
from callbot.settings.plugins import PluginsSettings
from callbot.settings.server import ServerSettings
from callbot.settings.twilio import TwilioSettings


class Settings(
    BaseSettings,
    SettingsSection,
    metaclass=Singleton.from_meta(ModelMetaclass),  # type: ignore[misc]
):
    """
    Encapsulates all application settings and instantiates a singleton.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        yaml_file="config.yaml",
    )

    backend: str = "openai"
    server: ServerSettings = ServerSettings()
    db: DBSettings = DBSettings()
    twilio: TwilioSettings = TwilioSettings()
    openai: OpenAISettings = OpenAISettings()
    elevenlabs: ElevenlabsSettings = ElevenlabsSettings()
    logging: LoggingSettings = LoggingSettings()
    misc: MiscSettings = MiscSettings()
    # TODO: This is dumped without applying serialization rules.
    plugins: PluginsSettings = PluginsSettings()

    _plugin_cache: dict[str, SettingsSection] = {}

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YamlConfigSettingsSource(settings_cls),
        )

    def plugin[S: SettingsSection](self, section_class: type[S]) -> S:
        if section_class.__qualname__ in self._plugin_cache:
            return cast(S, self._plugin_cache[section_class.__qualname__])
        name = section_class.section_name()
        data = self.plugins.__pydantic_extra__.get(name)  # type: ignore[union-attr]
        if data is None:
            # Assume the section model has defaults for all fields.
            settings_section = section_class()
        else:
            settings_section = section_class.model_validate(data)
        self._plugin_cache[section_class.__qualname__] = settings_section
        return settings_section


# The following is needed because PyYAML is annoying.
# Source: https://stackoverflow.com/a/45004775/

yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str  # type: ignore[attr-defined]


def repr_str(dumper: Any, data: Any) -> Any:
    if '\n' in data:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    return dumper.org_represent_str(data)


yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
