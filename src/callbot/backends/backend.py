from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import Event
from types import TracebackType
from typing import Self, TYPE_CHECKING

from callbot.schemas.contact import Contact

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class Backend(ABC):
    """
    Defines the interface for all conversation backends.

    Instantiated per call, just like the `CallManager`.
    """

    _contact_info: Contact | None
    _contact_info_ready: Event

    def __init__(self):
        self._contact_info = None
        self._contact_info_ready = Event()

    @property
    def contact_info(self) -> Contact | None:
        return self._contact_info

    @contact_info.setter
    def contact_info(self, contact_info: Contact) -> None:
        self._contact_info = contact_info
        self._contact_info_ready.set()

    async def get_contact_info_when_ready(self) -> Contact:
        await self._contact_info_ready.wait()
        assert self._contact_info is not None
        return self._contact_info

    async def __aenter__(self) -> Self:
        """Allows usage of an instance as an `async` context manager."""
        return self

    async def __aexit__[E: BaseException](
        self,
        exc_type: type[E] | None,
        exc_val: E | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exits the `async with`-block."""
        pass

    async def init_session(self) -> None:
        """
        Initializes the conversation session with the actual backend.

        This method exists due to the assumption that this step needs to be done
        with a coroutine and thus the `__init__` method will not suffice.

        The very first thing the `CallManager.run` method does, is await this.
        """
        # TODO: Maybe we can just use `__aenter__` instead?
        pass

    @abstractmethod
    async def listen(self, call_manager: CallManager) -> None:
        ...

    @abstractmethod
    async def send_audio(self, payload: str) -> None:
        ...

    @abstractmethod
    async def send_text(self, payload: str) -> None:
        ...

    @abstractmethod
    def get_transcript(self) -> str:
        ...
