from collections.abc import Callable
from datetime import time
from functools import cache
from ipaddress import IPv4Address
from logging import CRITICAL, INFO, getLevelNamesMapping
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, TypeAlias

import yaml
from annotated_types import Ge, Le
from caseutil import to_snake
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    IPvAnyAddress,
    PlainSerializer,
    PositiveInt,
    SecretStr,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapSerializer,
    WrapValidator,
    field_validator,
)
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo
from pydantic.main import IncEx
from pydantic_core.core_schema import SerializerFunctionWrapHandler
from pydantic_extra_types.phone_numbers import PhoneNumberValidator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from sqlalchemy import URL

from callbot.auth.algorithm import Algorithm, DEFAULT_ALGORITHM
from callbot.misc.singleton import Singleton
from callbot.misc.util import is_subclass
from callbot.types import StrDict


LOG_LEVELS = getLevelNamesMapping()


def log_level_num(v: object, handler: ValidatorFunctionWrapHandler) -> int:
    try:
        number = handler(v)
        assert isinstance(number, int)
        return number
    except ValidationError as err:
        if isinstance(v, str) and err.errors()[0]['type'] == 'int_parsing':
            if (number := LOG_LEVELS.get(v.upper())) is not None:
                return number
        raise err


def valid_file_path(v: object, handler: ValidatorFunctionWrapHandler) -> object:
    path: Path = handler(v)
    try:
        if path.is_file():
            return path
    except OSError:
        pass
    raise ValueError("Path is not a file")


def shorten_string(max_length: int) -> Callable[[str], str]:
    def inner(s: str) -> str:
        return f"{s[:max_length - 3]}..." if len(s) > max_length else s
    return inner


NoneAsEmptyStr = BeforeValidator(lambda v: "" if v is None else v)
NoneAsEmptyList = BeforeValidator(lambda v: [] if v is None else v)
NoneAsEmptyDict = BeforeValidator(lambda v: {} if v is None else v)

DBURLQuery = Annotated[dict[str, list[str] | str], NoneAsEmptyDict]
FloatOpenAISpeed = Annotated[float, Ge(0.25), Le(1.5)]
FloatOpenAITemperature = Annotated[float, Ge(0.6), Le(1.2)]
IntLogLevel = Annotated[PositiveInt, Le(CRITICAL), WrapValidator(log_level_num)]
LogModules = Annotated[dict[str, bool], NoneAsEmptyDict]
OpenAIVoice: TypeAlias = Literal[
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "onyx",
    "nova",
    "sage",
    "shimmer",
    "verse",
]
PathFileExists = Annotated[Path, WrapValidator(valid_file_path)]
Str128 = Annotated[str, PlainSerializer(shorten_string(128))]
StrPhone = Annotated[str, PhoneNumberValidator(number_format="E164")]
StrNoneAsEmpty = Annotated[str, NoneAsEmptyStr]
SecretStrNoneAsEmpty = Annotated[SecretStr, NoneAsEmptyStr]


def workaround_shorten_128(
    value: object,
    handler: SerializerFunctionWrapHandler,
) -> object:
    """
    https://github.com/pydantic/pydantic/issues/6830
    """
    if isinstance(value, str):
        return shorten_string(128)(value)
    return handler(value)


def get_text_from_file_or_str(value: Path | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value.read_text().strip()
    return value


class SettingsSection(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
    )

    @field_validator("*", mode="wrap")
    def _none_as_default_model(
        cls,
        v: Any,
        handler: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
    ) -> Any:
        try:
            return handler(v)
        except ValidationError as e:
            if v is None and e.errors()[0]["type"] == "model_type":
                assert info.field_name is not None
                field_info: FieldInfo = cls.model_fields[info.field_name]
                if is_subclass(field_info.annotation, SettingsSection):
                    try:
                        return field_info.get_default(call_default_factory=True)
                    except Exception:
                        raise e from None
            raise e

    @classmethod
    @cache
    def section_name(cls) -> str:
        return to_snake(cls.__name__.rsplit("Settings", maxsplit=1)[0])

    def model_dump_yaml(
        self,
        indent: int | None = None,
        width: int = 4096,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
    ) -> str:
        data = self.model_dump(
            mode="json",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
        )
        return yaml.safe_dump(
            data,
            allow_unicode=True,
            indent=indent,
            sort_keys=False,
            width=width,
        )


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


class TwilioSettings(SettingsSection):
    account_sid: StrNoneAsEmpty = ""
    auth_token: SecretStrNoneAsEmpty = SecretStr("")
    phone_number: StrPhone | None = None
    max_parallel_calls: PositiveInt = 1


class SessionSettings(SettingsSection):
    instructions: Annotated[
        PathFileExists | Str128 | None,
        Field(union_mode="left_to_right"),
        WrapSerializer(workaround_shorten_128),
    ] = None
    model: Literal[
        "gpt-4o-mini-realtime-preview",
        "gpt-4o-mini-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview",
        "gpt-4o-realtime-preview-2024-10-01",
        "gpt-4o-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview-2025-06-03",
    ] = "gpt-4o-realtime-preview-2025-06-03"
    speed: FloatOpenAISpeed = 1.0
    temperature: FloatOpenAITemperature = 0.8
    voice: OpenAIVoice = "sage"


class OpenAISettings(SettingsSection):
    REALTIME_BASE_URL: ClassVar[str] = "wss://api.openai.com/v1/realtime"
    AUDIO_FORMAT: ClassVar[
        Literal["pcm16", "g711_ulaw", "g711_alaw"]
    ] = "g711_ulaw"

    api_key: SecretStrNoneAsEmpty = SecretStr("")
    init_conversation_prompt: Annotated[
        PathFileExists | Str128 | None,
        Field(union_mode="left_to_right"),
        WrapSerializer(workaround_shorten_128),
    ] = None
    log_event_types: list[str] = [
        "input_audio_buffer.committed",
        "input_audio_buffer.speech_started",
        "input_audio_buffer.speech_stopped",
        "rate_limits.updated",
        "response.content.done",
        "response.done",
        "session.created",
        "session.updated",
    ]
    session: SessionSettings = SessionSettings()

    @property
    def realtime_stream_url(self) -> str:
        return f"{self.REALTIME_BASE_URL}?model={self.session.model}"

    def get_realtime_auth_headers(self) -> StrDict:
        if not self.api_key:
            raise RuntimeError("No OpenAI API key configured")
        return {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "OpenAI-Beta": "realtime=v1",
        }

    def get_init_conversation_prompt(self) -> str | None:
        return get_text_from_file_or_str(self.init_conversation_prompt)

    def get_session_instructions(self) -> str | None:
        return get_text_from_file_or_str(self.session.instructions)

    @classmethod
    def section_name(cls) -> str:
        return "openai"


class ScheduleSettings(SettingsSection):
    business_start: time = time(hour=8)
    business_end: time = time(hour=18)
    business_days: frozenset[Literal[0, 1, 2, 3, 4, 5, 6]] = frozenset({0, 1, 2, 3, 4})
    retry_delay_hours: PositiveInt = 4


class LoggingSettings(SettingsSection):
    level: IntLogLevel = INFO
    format: str = "<level>{level: <8}</level> | <level>{message}</level> | <cyan>{name}</cyan>"
    modules: LogModules = {
        "aiosqlite": False,
        "sqlalchemy": False,
        "websockets": False,
    }


class MiscSettings(SettingsSection):
    default_phone_region: str | None = None
    mode: Literal["testing", "production"] = "testing"


class PluginsSettings(SettingsSection):
    model_config = ConfigDict(extra="allow")


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

    server: ServerSettings = ServerSettings()
    db: DBSettings = DBSettings()
    twilio: TwilioSettings = TwilioSettings()
    openai: OpenAISettings = OpenAISettings()
    schedule: ScheduleSettings = ScheduleSettings()
    logging: LoggingSettings = LoggingSettings()
    misc: MiscSettings = MiscSettings()
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
            return self._plugin_cache[section_class.__qualname__]
        name = section_class.section_name()
        data = self.plugins.__pydantic_extra__.get(name)
        if data is None:
            # Assume the section model has defaults for all fields.
            section = section_class()
        else:
            section = section_class.model_validate(data)
        self._plugin_cache[section_class.__qualname__] = section
        return section


# The following is needed because PyYAML is annoying.
# Source: https://stackoverflow.com/a/45004775/

yaml.SafeDumper.org_represent_str = yaml.SafeDumper.represent_str  # type: ignore[attr-defined]


def repr_str(dumper: Any, data: Any) -> Any:
    if '\n' in data:
        return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='|')
    return dumper.org_represent_str(data)


yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)
