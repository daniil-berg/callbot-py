from collections.abc import Callable
from logging import CRITICAL, getLevelNamesMapping
from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from annotated_types import Ge, Le
from pydantic import (
    BeforeValidator,
    PlainSerializer,
    PositiveInt,
    SecretStr,
    ValidationError,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)
from pydantic_extra_types.phone_numbers import PhoneNumberValidator


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
OpenAIAudioTranscriptionModel = Literal[
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "whisper-1",
]
OpenAIMaxResponseOutputTokens = Annotated[int, Ge(1), Le(4096)] | Literal["inf"]
OpenAIModalities = (
    tuple[Literal["text", "audio"]] |
    tuple[Literal["text"], Literal["audio"]] |
    tuple[Literal["audio"], Literal["text"]]
)
OpenAITurnDetectionThreshold = Annotated[float, Ge(0.0), Le(1.0)]
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
