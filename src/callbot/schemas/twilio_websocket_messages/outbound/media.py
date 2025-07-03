from typing import Literal, Self

from pydantic import BaseModel


class MediaInner(BaseModel):
    payload: str


class Media(BaseModel):
    event: Literal["media"] = "media"
    streamSid: str
    media: MediaInner

    @classmethod
    def with_payload(cls, payload: str, sid: str) -> Self:
        return cls(streamSid=sid, media=MediaInner(payload=payload))
