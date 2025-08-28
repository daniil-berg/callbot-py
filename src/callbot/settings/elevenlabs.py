from typing import Annotated, ClassVar, Literal
from urllib.parse import urlencode

from annotated_types import Le, Len, Ge
from elevenlabs import VoiceSettings as _VoiceSettings
from elevenlabs import GenerationConfig as _GenerationConfig
from pydantic import SecretStr

from callbot.settings._section import SettingsSection
from callbot.settings._validators_types import SecretStrNoneAsEmpty
from callbot.types import StrDict

ElevenlabsAudioFormat = Literal[
    "mp3_22050_32",
    "mp3_44100_32",
    "mp3_44100_64",
    "mp3_44100_96",
    "mp3_44100_128",
    "mp3_44100_192",
    "pcm_8000",
    "pcm_16000",
    "pcm_22050",
    "pcm_44100",
    "pcm_48000",
    "ulaw_8000",
    "alaw_8000",
    "opus_48000_32",
    "opus_48000_64",
    "opus_48000_96",
    "opus_48000_128",
    "opus_48000_192",
]


class VoiceSettings(SettingsSection, _VoiceSettings):
    pass


class GenerationConfig(SettingsSection, _GenerationConfig):
    pass


class ElevenlabsSettings(SettingsSection):
    TTS_BASE_URL: ClassVar[str] = "wss://api.elevenlabs.io/v1/text-to-speech"

    api_key: SecretStrNoneAsEmpty = SecretStr("")
    # Path parameter:
    voice_id: str | None = None
    # Query parameters:
    authorization: SecretStrNoneAsEmpty | None = None
    model_id: str | None = None
    language_code: Annotated[str, Len(2)] | None = None
    enable_logging: bool | None = None
    enable_ssml_parsing: bool | None = None
    output_format: Literal["ulaw_8000"] = "ulaw_8000"
    inactivity_timeout: Annotated[int, Ge(1), Le(180)] | None = None
    sync_alignment: bool | None = None
    auto_mode: bool | None = None
    apply_text_normalization: Literal["on", "off", "auto"] | None = None
    seed: Annotated[int, Ge(0), Le(4294967295)] | None = None
    # Message properties:
    voice_settings: VoiceSettings | None = None
    generation_config: GenerationConfig | None = None

    @property
    def stream_url(self) -> str:
        if not self.voice_id:
            raise RuntimeError("Elevenlabs voice ID not configured")
        url = f"{self.TTS_BASE_URL}/{self.voice_id}/multi-stream-input"
        params = self.model_dump(
            exclude={"api_key", "voice_id", "voice_settings", "generation_config"},
            exclude_none=True,
        )
        if params:
            url += f"?{urlencode(params)}"
        return url

    def get_auth_headers(self) -> StrDict:
        if not self.api_key:
            raise RuntimeError("No Elevenlabs API key configured")
        return {
            "xi-api-key": self.api_key.get_secret_value(),
            # "Content-Type": "application/json",
        }

    @classmethod
    def section_name(cls) -> str:  # type: ignore[override]
        return "elevenlabs"
