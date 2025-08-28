from typing import Literal, Union

from pydantic import BaseModel

from callbot.settings.elevenlabs import GenerationConfig, VoiceSettings


class InitializeConnection(BaseModel):
    text: Literal[" "] = " "
    voice_settings: VoiceSettings | None = None
    generation_config: GenerationConfig | None = None


class SendText(BaseModel):
    text: str
    try_trigger_generation: bool = False
    flush: bool = False
    voice_settings: VoiceSettings | None = None
    generator_config: GenerationConfig | None = None


class CloseConnection(BaseModel):
    text: Literal[""] = ""


###
# Multi-Context Websocket


class InitializeContext(BaseModel):
    text: str
    context_id: str | None = None
    voice_settings: VoiceSettings | None = None
    generation_config: GenerationConfig | None = None


class SendTextMulti(BaseModel):
    text: str
    context_id: str | None = None
    flush: bool = False


class FlushContextClient(BaseModel):
    context_id: str
    flush: Literal[True] = True
    text: str | None = None


class CloseContextClient(BaseModel):
    context_id: str
    close_context: Literal[True] = True


class CloseSocketClient(BaseModel):
    close_socket: Literal[True] = True


class KeepContextAlive(BaseModel):
    text: Literal[""] = ""
    context_id: str


AnySendMessage = Union[
    CloseContextClient,
    CloseSocketClient,
    InitializeContext,
    FlushContextClient,
    KeepContextAlive,
    SendTextMulti,
]
