# TODO: Put this into its own utility pacakge and publish it. (Abstract `get_entrypoints`)

from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import gather
from importlib.metadata import EntryPoint, EntryPoints, entry_points
from typing import Any, ClassVar, Self

from loguru import logger as log

from callbot.misc.generic_insight import GenericInsightMixin1
from callbot.misc.util import is_subclass


class Hook:
    __loaded_callbacks: ClassVar[dict[type[Hook], dict[str, Callback]]] = {}

    @classmethod
    def get_callbacks_for(cls, hook: Self | type[Self]) -> dict[str, Callback]:
        hook_cls = hook.__class__ if isinstance(hook, Hook) else hook
        if hook_cls not in cls.__loaded_callbacks:
            cls.__loaded_callbacks[hook_cls] = {}
            for plugin in cls.get_entrypoints():
                cls._update_callbacks(plugin)
        return cls.__loaded_callbacks[hook_cls]

    @staticmethod
    def get_entrypoints() -> EntryPoints:
        return entry_points(group="callbot.callbacks")

    @classmethod
    def _update_callbacks(cls, plugin: EntryPoint) -> None:
        callback_cls = plugin.load()
        if not is_subclass(callback_cls, Callback):
            log.error(f"{plugin.value} is not a hook callback class")
            return
        hook = callback_cls.get_hook()
        name = plugin.name
        try:
            callback = callback_cls()
        except Exception as e:
            log.error(f"Failed to instantiate hook callback {name}: {e}")
            return
        if hook not in cls.__loaded_callbacks:
            cls.__loaded_callbacks[hook] = {name: callback}
        else:
            cls.__loaded_callbacks[hook][name] = callback

    def __str__(self) -> str:
        return self.__class__.__name__

    async def dispatch(self) -> None:
        callbacks = Hook.get_callbacks_for(self)
        if not callbacks:
            log.debug(f"No callbacks to dispatch {self} to")
            return
        names, coroutines = zip(
            *((name, callback(self)) for name, callback in callbacks.items())
        )
        log.debug(f"Dispatching {self} to callbacks: {list(names)}")
        outputs = await gather(*coroutines, return_exceptions=True)
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
    def get_hook(cls) -> type[Hook]:
        return cls._get_type_arg(0)

    @classmethod
    def is_bound_to(cls, hook: Hook | type[Hook]) -> bool:
        if isinstance(hook, Hook):
            return cls._get_type_arg(0) is hook.__class__
        return cls._get_type_arg(0) is hook

    @abstractmethod
    async def __call__(self, hook: _H, /) -> None:
        ...
