from typing import Literal

from pydantic import BaseModel

from callbot.types import StrDict


class MediaFormat(BaseModel):
    encoding: str
    sampleRate: int
    channels: int


class StartInner(BaseModel):
    accountSid: str
    streamSid: str
    callSid: str
    tracks: tuple[Literal["inbound", "outbound"]] | tuple[Literal["inbound"], Literal["outbound"]] | tuple[Literal["outbound"], Literal["inbound"]]
    customParameters: StrDict
    mediaFormat: MediaFormat


class Start(BaseModel):
    event: Literal["start"] = "start"
    sequenceNumber: str
    start: StartInner
    streamSid: str
