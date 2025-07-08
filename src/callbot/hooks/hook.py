from abc import ABC, abstractmethod
from asyncio import gather
from importlib.metadata import entry_points
from typing import Any

from loguru import logger as log

from callbot.misc.generic_insight import GenericInsightMixin1
from callbot.misc.util import is_subclass


class Hook:
    async def dispatch(self) -> None:
        names = []
        callbacks = []
        for plugin in entry_points(group="callbot.callbacks"):
            callback_cls = plugin.load()
            if not is_subclass(callback_cls, Callback):
                log.error(f"{plugin.value} is not a hook callback class")
                continue
            if not callback_cls.is_bound_to(self):
                continue
            name = plugin.name
            try:
                callback = callback_cls()
            except Exception as e:
                log.error(f"Failed to instantiate hook callback {name}: {e}")
                continue
            callbacks.append(callback(self))
            names.append(name)
        log.debug(f"Dispatching {self.__class__.__name__}. Callbacks: {names}")
        outputs = await gather(*callbacks, return_exceptions=True)
        for idx, output in enumerate(outputs):
            if isinstance(output, Exception):
                log.error(f"Exception in hook callback {names[idx]}: {output}")


class Callback[_H: Hook](GenericInsightMixin1[_H], ABC):
    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        hook = cls._get_type_arg(0)
        if not is_subclass(hook, Hook):
            raise TypeError(f"{hook.__class__.__name__} is not a hook")

    @classmethod
    def is_bound_to(cls, hook: Hook | type[Hook]) -> bool:
        if isinstance(hook, Hook):
            return cls._get_type_arg(0) is hook.__class__
        return cls._get_type_arg(0) is hook

    @abstractmethod
    async def __call__(self, hook: _H, /) -> None:
        ...
