from typing import Literal

from openai.types.beta.realtime import conversation_item_truncate_event as base


class ConversationItemTruncateEvent(base.ConversationItemTruncateEvent):
    type: Literal["conversation.item.truncate"] = "conversation.item.truncate"
