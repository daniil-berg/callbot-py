from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from openai.types.beta.realtime.conversation_item import ConversationItem
from .hook import Hook

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


@dataclass
class BeforeConversationStartHook(Hook):
    conversation_item: ConversationItem
    call_manager: CallManager
