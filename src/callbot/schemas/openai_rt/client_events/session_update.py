from typing import Annotated, Literal, Self

from openai.types.beta.realtime import session_update_event as base
from pydantic import Field

from callbot.settings import FloatOpenAISpeed, FloatOpenAITemperature, Settings
from callbot.schemas.openai_rt.function import Arguments, Function


class SessionInputAudioTranscription(base.SessionInputAudioTranscription):
    model: Literal["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"] | None = None


class SessionTurnDetection(base.SessionTurnDetection):
    prefix_padding_ms: Annotated[int, Field(ge=0)] | None = None
    silence_duration_ms: Annotated[int, Field(ge=0)] | None = None
    threshold: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    type: Literal["server_vad", "semantic_vad"] | None = None


class Session(base.Session):
    input_audio_transcription: SessionInputAudioTranscription | None = None
    max_response_output_tokens: Annotated[int, Field(ge=1, le=4096)] | Literal["inf"] | None = None
    modalities: tuple[Literal["text", "audio"]] | tuple[Literal["text"], Literal["audio"]] | tuple[Literal["audio"], Literal["text"]] | None = None  # type: ignore[assignment]
    speed: FloatOpenAISpeed | None = None
    temperature: FloatOpenAITemperature | None = None
    tools: list[Function[Arguments]] | None = None  # type: ignore[assignment]
    tracing: Literal["auto"] | None = None
    turn_detection: SessionTurnDetection | None = None


class SessionUpdateEvent(base.SessionUpdateEvent):
    session: Session
    type: Literal["session.update"] = "session.update"

    @classmethod
    def from_settings(cls) -> Self:
        settings = Settings()
        return cls(
            session=Session(
                input_audio_format=settings.openai.AUDIO_FORMAT,
                instructions=settings.openai.get_session_instructions(),
                modalities=("text", "audio"),
                output_audio_format=settings.openai.AUDIO_FORMAT,
                speed=settings.openai.session.speed,
                temperature=settings.openai.session.temperature,
                tools=Function.all(),
                turn_detection=SessionTurnDetection(
                    type="server_vad",
                ),
                voice=settings.openai.session.voice,
            )
        )
