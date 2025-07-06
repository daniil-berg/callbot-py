from typing import Literal

from pydantic import BaseModel

from .algorithm import Algorithm, DEFAULT_ALGORITHM


class Header(BaseModel):
    typ: Literal["jwt"] = "jwt"
    alg: Algorithm = DEFAULT_ALGORITHM
