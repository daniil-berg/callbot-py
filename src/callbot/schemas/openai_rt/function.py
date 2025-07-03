from __future__ import annotations

import json
from typing import Any, ClassVar, Literal, TYPE_CHECKING

from caseutil import to_snake
from openai.types.beta.realtime.session_update_event import SessionTool as _SessionTool
from openai.types.beta.realtime.realtime_response import RealtimeResponse
from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class SessionTool(_SessionTool):
    type: Literal["function"] = "function"


class Arguments(BaseModel):
    pass


class Function[ArgT: Arguments](SessionTool):
    model_config = ConfigDict(
        validate_default=True,
    )
    registry: ClassVar[
        dict[str, type[Function[Any]]]
    ] = {}

    arguments: ArgT | None = None

    def __init_subclass__(cls, register: bool = False, **kwargs: Any) -> None:
        if register:
            Function.registry[cls.get_name()] = cls

    @field_validator("name", mode="plain")
    def _get_name(cls, v: str | None) -> str:
        if v is None:
            return cls.get_name()
        return v

    @field_validator("description", mode="plain")
    def _get_description(cls, v: str | None) -> str:
        if v is None:
            return cls.get_description()
        return v

    @field_validator("parameters", mode="plain")
    def _get_parameters(cls, v: dict[str, Any] | None) -> dict[str, Any]:
        if v is None:
            return cls.get_parameters()
        return v

    @staticmethod
    def all() -> list[Function[Arguments]]:
        return [subclass() for subclass in Function.registry.values()]

    @staticmethod
    def from_response(response: RealtimeResponse) -> Function[Arguments] | None:
        if response.output is None:
            return None
        for output in response.output:
            if output.type != "function_call" or output.name is None:
                continue
            print(f"Function call detected: {output.name}")
            if (func_cls := Function.registry.get(output.name)) is None:
                continue
            if output.arguments is None:
                args = None
            else:
                args = json.loads(output.arguments)
            return func_cls(arguments=args)
        return None

    @classmethod
    def get_name(cls) -> str:
        return to_snake(cls.__name__)

    @classmethod
    def get_description(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def get_parameters(cls) -> dict[str, Any]:
        # TODO: Define custom `Parameter` and `Parameters` models to simplify subclassing.
        raise NotImplementedError()

    async def __call__(self, call: CallManager | None = None) -> None:
        pass
