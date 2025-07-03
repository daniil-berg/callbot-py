from typing import Literal

from openai.types.beta.realtime import input_audio_buffer_append_event as base


class InputAudioBufferAppendEvent(base.InputAudioBufferAppendEvent):
    type: Literal["input_audio_buffer.append"] = "input_audio_buffer.append"
