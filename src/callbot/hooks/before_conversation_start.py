from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from callbot.schemas.openai_rt.server_events import ConversationItem  # type: ignore[attr-defined]
from .hook import Hook

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


@dataclass
class BeforeConversationStart(Hook):
    conversation_item: ConversationItem
    call_manager: CallManager
