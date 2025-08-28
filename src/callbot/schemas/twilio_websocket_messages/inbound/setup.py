from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Setup(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
    )
    type: Literal["setup"] = "setup"
    session_id: str
    call_sid: str
    parent_call_sid: str
    from_: Annotated[str, Field(alias="from")]
    to: str
    forwarded_from: str
    caller_name: str
    call_type: str
    account_sid: str
    direction: Literal["inbound", "outbound", "outbound-api"]
    custom_parameters: dict[str, str] = Field(default_factory=dict)
