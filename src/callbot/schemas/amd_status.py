from typing import Literal

from pydantic import BaseModel, ConfigDict, NonNegativeFloat
from pydantic.alias_generators import to_pascal

from callbot.settings._validators_types import TwilioAccountSID


AnsweredBy = Literal[
    "machine_start",
    "human",
    "fax",
    "unknown",
    "machine_end_beep",
    "machine_end_silence",
    "machine_end_other",
]


class AMDStatus(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_pascal,
        validate_by_name=True,
    )
    call_sid: str
    account_sid: TwilioAccountSID
    answered_by: AnsweredBy
    machine_detection_duration: NonNegativeFloat
