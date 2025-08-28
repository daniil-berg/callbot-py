from typing import Literal

from pydantic import BaseModel


class TextTokens(BaseModel):
    type: Literal["text"] = "text"
    token: str
    last: bool | None = None
    lang: str | None = None
    interruptible: bool | None = None
    preemptible: bool | None = None
