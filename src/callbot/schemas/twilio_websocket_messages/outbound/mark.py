from typing import Literal, Self

from pydantic import BaseModel


class MarkInner(BaseModel):
    name: str


class Mark(BaseModel):
    event: Literal["mark"] = "mark"
    streamSid: str
    mark: MarkInner

    @classmethod
    def with_name(cls, name: str, sid: str) -> Self:
        return cls(streamSid=sid, mark=MarkInner(name=name))
