from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Interrupt(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
    )
    type: Literal["interrupt"] = "interrupt"
    utterance_until_interrupt: str
    duration_until_interrupt_ms: int
