from typing import Annotated, Union

from pydantic import TypeAdapter, Field

from .clear import Clear
from .mark import Mark
from .media import Media


Message = TypeAdapter[Union[Clear, Mark, Media]](
    Annotated[
        Union[Clear, Mark, Media],
        Field(discriminator="event"),
    ]
)
