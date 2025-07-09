from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .hook import Hook

if TYPE_CHECKING:
    from callbot.call_manager import CallManager
    from callbot.functions import Function


@dataclass
class BeforeFunctionCallHook(Hook):
    function: Function[Any]
    call_manager: CallManager
