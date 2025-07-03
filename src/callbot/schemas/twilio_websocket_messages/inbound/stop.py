from typing import Literal

from pydantic import BaseModel


class StopInner(BaseModel):
    accountSid: str
    callSid: str


class Stop(BaseModel):
    event: Literal["stop"] = "stop"
    sequenceNumber: str
    stop: StopInner
    streamSid: str
