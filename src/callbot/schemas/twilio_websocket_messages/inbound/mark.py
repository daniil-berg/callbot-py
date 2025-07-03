from typing import Literal

from pydantic import BaseModel


class MarkInner(BaseModel):
    name: str


class Mark(BaseModel):
    event: Literal["mark"] = "mark"
    streamSid: str
    sequenceNumber: str
    mark: MarkInner
