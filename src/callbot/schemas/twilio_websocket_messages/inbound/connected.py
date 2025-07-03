from typing import Literal

from pydantic import BaseModel


class Connected(BaseModel):
    event: Literal["connected"] = "connected"
    protocol: str
    version: str
