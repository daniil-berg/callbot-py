from typing import Literal

from openai.types.beta.realtime import response_create_event as base


class ResponseCreateEvent(base.ResponseCreateEvent):
    type: Literal["response.create"] = "response.create"

    @classmethod
    def default_json(cls) -> str:
        return cls().model_dump_json(exclude_none=True)
