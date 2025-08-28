from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Prompt(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
    )
    type: Literal["prompt"] = "prompt"
    voice_prompt: str
    lang: str
    last: bool
