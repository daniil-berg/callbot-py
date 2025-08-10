from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal

from pydantic import Field, SecretStr, WrapSerializer, computed_field
from pydantic_core.core_schema import SerializerFunctionWrapHandler

from callbot.schemas.openai_rt.client_events.session import (
    Session,
    SessionTurnDetection,
)
from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import (
    FloatOpenAISpeed,
    FloatOpenAITemperature,
    PathFileExists,
    SecretStrNoneAsEmpty,
    Str128,
    shorten_string,
)
from callbot.types import StrDict


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


class SessionSettings(SettingsSection, Session):
    input_audio_format: Literal["g711_ulaw"] = "g711_ulaw"
    instructions: Str128 | None = None
    instructions_file: PathFileExists | None = None
    modalities: tuple[Literal["audio"], Literal["text"]] = ("audio", "text")
    model: Literal[
        "gpt-4o-mini-realtime-preview",
        "gpt-4o-mini-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview",
        "gpt-4o-realtime-preview-2024-10-01",
        "gpt-4o-realtime-preview-2024-12-17",
        "gpt-4o-realtime-preview-2025-06-03",
    ] = "gpt-4o-realtime-preview-2025-06-03"
    output_audio_format: Literal["g711_ulaw"] = "g711_ulaw"
    speed: FloatOpenAISpeed = 1.0
    temperature: FloatOpenAITemperature = 0.8
    turn_detection: SessionTurnDetection | None = SessionTurnDetection(
        type="server_vad",
    )

    def model_post_init(self, context: Any, /) -> None:
        self._update_instructions()

    def _update_instructions(self) -> None:
        if self.instructions_file:
            self.instructions = self.instructions_file.read_text().strip()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tool_names(self) -> list[str]:
        if self.tools is None:
            return []
        return sorted(tool.name for tool in self.tools if tool.name)


class OpenAISettings(SettingsSection):
    REALTIME_BASE_URL: ClassVar[str] = "wss://api.openai.com/v1/realtime"

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
        return _get_text_from_file_or_str(self.init_conversation_prompt)

    @classmethod
    def section_name(cls) -> str:  # type: ignore[override]
        return "openai"


def _get_text_from_file_or_str(value: Path | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, Path):
        return value.read_text().strip()
    return value
