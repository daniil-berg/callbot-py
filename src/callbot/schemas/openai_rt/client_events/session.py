from typing import Literal

from openai.types.beta.realtime.session_update_event import (
    Session as _Session,
    SessionInputAudioTranscription as _SessionInputAudioTranscription,
    SessionTurnDetection as _SessionTurnDetection,
)
from pydantic import NonNegativeInt

from callbot.settings._validators_types import (
    FloatOpenAISpeed,
    FloatOpenAITemperature,
    OpenAIAudioTranscriptionModel,
    OpenAIMaxResponseOutputTokens,
    OpenAIModalities,
    OpenAITurnDetectionThreshold,
)


class SessionInputAudioTranscription(_SessionInputAudioTranscription):
    model: OpenAIAudioTranscriptionModel | None = None


class SessionTurnDetection(_SessionTurnDetection):
    prefix_padding_ms: NonNegativeInt | None = None
    silence_duration_ms: NonNegativeInt | None = None
    threshold: OpenAITurnDetectionThreshold | None = None
    type: Literal["server_vad", "semantic_vad"] | None = None


class Session(_Session):
    input_audio_transcription: SessionInputAudioTranscription | None = None
    max_response_output_tokens: OpenAIMaxResponseOutputTokens | None = None
    modalities: OpenAIModalities | None = None  # type: ignore[assignment]
    speed: FloatOpenAISpeed | None = None
    temperature: FloatOpenAITemperature | None = None
    tracing: Literal["auto"] | None = None
    turn_detection: SessionTurnDetection | None = None
