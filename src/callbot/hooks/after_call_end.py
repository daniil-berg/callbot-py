from __future__ import annotations

from typing import TYPE_CHECKING

from .hook import Hook

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class AfterCallEndHook(Hook):
    def __init__(self, call_manager: CallManager) -> None:
        self.call_manager = call_manager
