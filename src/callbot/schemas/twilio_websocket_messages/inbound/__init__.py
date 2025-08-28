from typing import Annotated, TypeAlias, Union

from pydantic import TypeAdapter, Field

from .connected import Connected
from .error import Error
from .interrupt import Interrupt
from .mark import Mark
from .media import Media
from .prompt import Prompt
from .setup import Setup
from .start import Start
from .stop import Stop


AnyInboundMediaStreamMessage: TypeAlias = Connected | Start | Media | Stop | Mark
MediaStreamMessage = TypeAdapter[AnyInboundMediaStreamMessage](
    Annotated[
        AnyInboundMediaStreamMessage,
        Field(discriminator="event"),
    ]
)

AnyInboundConversationRelayMessage: TypeAlias = Error | Interrupt | Prompt | Setup
ConversationRelayMessage = TypeAdapter[AnyInboundConversationRelayMessage](
    Annotated[
        AnyInboundConversationRelayMessage,
        Field(discriminator="type"),
    ]
)

Message = TypeAdapter(
    Union[
        Annotated[
            AnyInboundMediaStreamMessage,
            Field(discriminator="event"),
        ],
        Annotated[
            AnyInboundConversationRelayMessage,
            Field(discriminator="type"),
        ],
    ]
)
