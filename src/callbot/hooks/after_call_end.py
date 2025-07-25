from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .hook import Hook

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


@dataclass
class AfterCallEndHook(Hook):
    call_manager: CallManager
    exceptions: ExceptionGroup | None
