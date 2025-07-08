from typing import Any, Optional, TYPE_CHECKING

from callbot.exceptions import EndCall
from callbot.schemas.openai_rt.function import Arguments as _Arguments, Function

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class Arguments(_Arguments):
    reason: str


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
                    "type": "string",
                    "description": "The reason you consider the conversation "
                                   "to be over. One or two sentences.",
                    "examples": [
                        "The other person said good-bye.",
                        "I reached an answering machine/voicemail.",
                        "I asked something, but got no response for 8 seconds.",
                        "I only heard static/noise. The connection was faulty.",
                    ],
                },
            },
            "required": ["reason"],
            "additionalProperties": False,
        }

    async def __call__(self, call: Optional["CallManager"] = None) -> None:
        assert self.arguments is not None
        assert call is not None
        msg = f"Reason: {self.arguments.reason}"
        if call.contact_info:
            msg += f" Contact: {call.contact_info.model_dump_json()}"
        raise EndCall(msg)
