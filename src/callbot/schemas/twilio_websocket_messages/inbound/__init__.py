from typing import Annotated, TypeAlias

from pydantic import TypeAdapter, Field

from .connected import Connected
from .mark import Mark
from .media import Media
from .start import Start
from .stop import Stop


AnyInboundMessage: TypeAlias = Connected | Start | Media | Stop | Mark
Message = TypeAdapter[AnyInboundMessage](
    Annotated[
        AnyInboundMessage,
        Field(discriminator="event"),
    ]
)
