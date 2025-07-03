from typing import Literal

from pydantic import BaseModel


class Clear(BaseModel):
    event: Literal["clear"] = "clear"
    streamSid: str
