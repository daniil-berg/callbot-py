from abc import ABC, abstractmethod
from asyncio import gather
from importlib.metadata import entry_points
from typing import Any

from loguru import logger as log

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
            if callback_cls.hook is not self.__class__:
                continue
            name = plugin.name
            try:
                callback = callback_cls()
            except Exception as e:
                log.error(f"Failed to instantiate hook callback {name}: {e}")
                continue
            callbacks.append(callback(self))
            names.append(name)
        outputs = await gather(*callbacks, return_exceptions=True)
        for idx, output in enumerate(outputs):
            if isinstance(output, Exception):
                log.error(f"Exception in hook callback {names[idx]}: {output}")


class Callback[_H: Hook](ABC):
    hook: type[_H]

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        if not hasattr(cls, "hook"):
            raise TypeError(f"{cls.__name__} does not define a hook")
        if not is_subclass(cls.hook, Hook):
            raise TypeError(f"{cls.hook.__class__.__name__} is not a hook")

    @abstractmethod
    async def __call__(self, __hook: _H, /) -> None:
        ...
