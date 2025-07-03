from typing import Literal, Self

from openai.types.beta.realtime import conversation_item_create_event as base

from ..server_events import ConversationItem, ConversationItemContent


class ConversationItemCreateEvent(base.ConversationItemCreateEvent):
    type: Literal["conversation.item.create"] = "conversation.item.create"

    @classmethod
    def with_user_prompt(cls, prompt: str) -> Self:
        return cls(
            item=ConversationItem(
                type="message",
                role="user",
                content=[
                    ConversationItemContent(
                        type="input_text",
                        text=prompt,
                    )
                ]
            )
        )
