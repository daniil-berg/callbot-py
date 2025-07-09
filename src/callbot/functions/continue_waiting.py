from typing import Any, Optional, TYPE_CHECKING

from loguru import logger as log

from callbot.functions import Arguments as _Arguments, Function

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class Arguments(_Arguments):
    reason: str


class ContinueWaiting(Function[Arguments], register=True):
    """Inspired by this post: https://community.openai.com/t/1105228"""
    @classmethod
    def get_description(cls) -> str:
        return (
            "Call this function when you receive input that is not directed "
            "towards you, This will skip this input and wait for the next. "
            "This is also a tool you can use to let the other person have the "
            "last word, which you should do often (as there is no utility in "
            "responding to thanks or superfluous conversation)."
            "ALWAYS PASS ARGUMENTS IN VALID JSON!"
        )

    @classmethod
    def get_parameters(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "The reason you think the last input was "
                                   "not directed towards you. "
                                   "One or two sentences.",
                    "examples": [
                        "The other person just coughed.",
                        "There was just some background noise.",
                        "The other person said something to someone else.",
                    ],
                },
            },
            "required": ["reason"],
            "additionalProperties": False,
        }

    async def __call__(self, call: Optional["CallManager"] = None) -> None:
        assert self.arguments is not None
        log.info(f"Waiting. {self.arguments.reason}")
