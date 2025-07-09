from collections.abc import Callable
from functools import cache
from typing import Any, Literal

import yaml
from caseutil import to_snake
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    field_validator,
)
from pydantic.fields import FieldInfo
from pydantic.main import IncEx

from callbot.misc.util import is_subclass


class SettingsSection(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
    )

    @field_validator("*", mode="wrap")
    def _none_as_default_model(
        cls,
        v: Any,
        handler: ValidatorFunctionWrapHandler,
        info: ValidationInfo,
    ) -> Any:
        try:
            return handler(v)
        except ValidationError as e:
            if v is None and e.errors()[0]["type"] == "model_type":
                assert info.field_name is not None
                field_info: FieldInfo = cls.model_fields[info.field_name]
                if is_subclass(field_info.annotation, SettingsSection):
                    try:
                        return field_info.get_default(call_default_factory=True)
                    except Exception:
                        raise e from None
            raise e

    @classmethod
    @cache
    def section_name(cls) -> str:
        return to_snake(cls.__name__.rsplit("Settings", maxsplit=1)[0])

    def model_dump_yaml(
        self,
        indent: int | None = None,
        width: int = 4096,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
    ) -> str:
        data = self.model_dump(
            mode="json",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
        )
        return yaml.safe_dump(
            data,
            allow_unicode=True,
            indent=indent,
            sort_keys=False,
            width=width,
        )
