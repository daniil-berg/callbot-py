from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .hook import Hook

if TYPE_CHECKING:
    from callbot.call_manager import CallManager
    from callbot.schemas.openai_rt.function import Function


class BeforeFunctionCallHook(Hook):
    def __init__(
        self,
        function: Function[Any],
        call_manager: CallManager,
    ) -> None:
        self.function = function
        self.call_manager = call_manager
