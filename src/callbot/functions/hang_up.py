from enum import StrEnum
from typing import Any, Optional, TYPE_CHECKING

from callbot.exceptions import EndCall
from callbot.functions import Arguments as _Arguments, Function

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class Reason(StrEnum):
    goodbye = "goodbye"
    voicemail = "voicemail"
    failure = "failure"
    other = "other"


class Arguments(_Arguments):
    reason: Reason
    explanation: str | None = None


class HangUp(Function[Arguments], register=True):
    @classmethod
    def get_description(cls) -> str:
        return (
            "Ends the call. Example scenarios for appropriate function calls: "
            "1) Conversation is over. The other person said good-bye. "
            "2) You reached an answering machine/voicemail. "
            "3) You got no response for a prolonged period of time. "
            "4) The connection was so bad, you only heard noise/static. "
            "ALWAYS PASS ARGUMENTS IN VALID JSON!"
        )

    @classmethod
    def get_parameters(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reason": {
                    "enum": [
                        "goodbye",
                        "voicemail",
                        "failure",
                        "other",
                    ],
                    "description": "The reason you consider the conversation "
                                   "to be over. Use \"goodbye\", if it ended "
                                   "normally. Use \"voicemail\", if you "
                                   "reached an answering machine/voicemail. "
                                   "Use \"failure\", if the connection was "
                                   "faulty or you were cut off from continuing "
                                   "the conversation. Use \"other\", for any "
                                   "other reason, and provide an explanation "
                                   "via the `explanation` property.",
                },
                "explanation": {
                    "type": "string",
                    "description": "If the reason is \"other\", describe it in "
                                   "one or two sentences with this argument. "
                                   "Otherwise omit this property.",
                },
            },
            "required": ["reason"],
            "additionalProperties": False,
        }

    async def __call__(self, call: Optional["CallManager"] = None) -> None:
        assert self.arguments is not None
        assert call is not None
        msg = f"Reason: '{self.arguments.reason}'"
        if self.arguments.reason == Reason.other:
            msg += f" ({self.arguments.explanation})"
        if call.contact_info:
            msg += f". Contact: {call.contact_info.model_dump_json()}"
        raise EndCall(msg)
