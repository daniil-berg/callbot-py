from __future__ import annotations

import json
from typing import Any, ClassVar, Literal, TYPE_CHECKING, cast

from caseutil import to_snake
from loguru import logger as log
from openai.types.beta.realtime.session_update_event import SessionTool as _SessionTool
from openai.types.beta.realtime.realtime_response import RealtimeResponse
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from pydantic._internal._model_construction import ModelMetaclass

from callbot.settings import Settings

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class SessionTool(_SessionTool):
    type: Literal["function"] = "function"


class Arguments(BaseModel):
    pass


class FunctionMeta(ModelMetaclass):
    registry: ClassVar[dict[str, type[Function[Any]]]] = {}

    def __new__(
        mcs,
        cls_name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        register: bool = False,
        **kwargs: Any,
    ) -> type[Any]:
        cls = cast(
            "type[Function[Any]]",
            super().__new__(mcs, cls_name, bases, namespace, **kwargs),
        )
        if register:
            mcs.registry[cls.get_name()] = cls
            # TODO: Catch validation errors.
            instance = cls()
            settings = Settings()
            if settings.openai.session.tools is None:
                settings.openai.session.tools = [instance]
            else:
                settings.openai.session.tools.append(instance)
        return cls

    @classmethod
    def get_by_name(cls, name: str) -> type[Function[Any]] | None:
        return cls.registry.get(name)


class Function[ArgT: Arguments](SessionTool, metaclass=FunctionMeta):
    model_config = ConfigDict(
        validate_default=True,
    )

    arguments: ArgT | None = None

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
    def from_response(response: RealtimeResponse) -> Function[Arguments] | None:
        if response.output is None:
            return None
        for output in response.output:
            if output.type != "function_call" or output.name is None:
                continue
            name = output.name
            log.debug(f"Function call detected: {name}")
            if (func_cls := FunctionMeta.get_by_name(name)) is None:
                continue
            if output.arguments is None:
                args = None
            else:
                args = json.loads(output.arguments)
            try:
                return func_cls(arguments=args)
            except ValidationError as e:
                log.error(f"Invalid arguments for '{name}': {e.json()}")
                return None
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
