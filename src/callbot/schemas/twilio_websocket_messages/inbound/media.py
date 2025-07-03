from typing import Literal

from pydantic import BaseModel


class MediaInner(BaseModel):
    track: Literal["inbound", "outbound"]
    chunk: int
    timestamp: int
    payload: str


class Media(BaseModel):
    event: Literal["media"] = "media"
    sequenceNumber: str
    media: MediaInner
    streamSid: str
