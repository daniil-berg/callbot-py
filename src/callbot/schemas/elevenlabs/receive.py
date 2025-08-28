from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, TypeAdapter
from pydantic.alias_generators import to_camel


class CommonModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
    )


class NormalizedAlignment(CommonModel):
    char_start_times_ms: list[int] | None = None
    chars_durations_ms: list[int] | None = None
    chars: list[str] | None = None


class Alignment(CommonModel):
    char_start_times_ms: list[int] | None = None
    chars_durations_ms: list[int] | None = None
    chars: list[str] | None = None


class AudioOutput(CommonModel):
    audio: str | None = None
    normalized_alignment: NormalizedAlignment | None = None
    alignment: Alignment | None = None


class FinalOutput(CommonModel):
    is_final: bool


AnyMessage = Union[
    AudioOutput,
    FinalOutput,
]
Message = TypeAdapter(AnyMessage)


class AudioOutputMulti(CommonModel):
    audio: str
    normalized_alignment: NormalizedAlignment | None = None
    alignment: Alignment | None = None
    context_id: str | None = None


class FinalOutputMulti(CommonModel):
    is_final: Literal[True] = True
    context_id: str | None = None


AnyReceiveMessage = Union[
    AudioOutputMulti,
    FinalOutputMulti,
]
ReceiveMessage = TypeAdapter(AnyReceiveMessage)
