from asyncio.exceptions import CancelledError
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

from loguru import logger as log
from pydantic import ValidationError
# TODO: Migrate to httpx-ws
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from callbot.schemas.elevenlabs.send import (
    AnySendMessage,
    CloseContextClient,
    CloseSocketClient,
    FlushContextClient,
    InitializeContext,
    SendTextMulti,
)
from callbot.schemas.elevenlabs.receive import (
    AnyReceiveMessage,
    ReceiveMessage,
)
from callbot.settings import Settings


class Elevenlabs:
    _websocket: connect
    _connection: ClientConnection
    _contexts: set[str | None]

    def __init__(self):
        super().__init__()
        settings = Settings()
        log.debug(f"Connecting to Elevenlabs Websocket: {settings.elevenlabs.stream_url}")
        self._websocket = connect(
            uri=settings.elevenlabs.stream_url,
            additional_headers=settings.elevenlabs.get_auth_headers(),
        )
        self._contexts = set()

    async def __aenter__(self) -> Self:
        self._connection = await self._websocket.__aenter__()
        return self

    async def __aexit__[E: BaseException](
        self,
        exc_type: type[E] | None,
        exc_val: E | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._connection.__aexit__(exc_type, exc_val, exc_tb)

    async def _send(self, message: AnySendMessage) -> None:
        serialized = message.model_dump_json(exclude_none=True)
        log.debug(f"Sending message to Elevenlabs: {serialized}")
        await self._connection.send(serialized)

    async def send_text(self, text: str, context_id: str | None = None) -> None:
        message: InitializeContext | SendTextMulti
        if context_id not in self._contexts:
            self._contexts.add(context_id)
            settings = Settings()
            message = InitializeContext(
                text=text,
                context_id=context_id,
                voice_settings=settings.elevenlabs.voice_settings,
                generation_config=settings.elevenlabs.generation_config,
            )
        else:
            message = SendTextMulti(
                text=text,
                context_id=context_id,
            )
        await self._send(message)

    async def flush_context(self, context_id: str) -> None:
        """Force generation of any buffered audio in the context."""
        await self._send(FlushContextClient(context_id=context_id))

    async def close_context(self, context_id: str) -> None:
        self._contexts.remove(context_id)
        await self._send(CloseContextClient(context_id=context_id))

    async def end_conversation(self) -> None:
        await self._send(CloseSocketClient())

    async def listen(self) -> AsyncIterator[AnyReceiveMessage | None]:
        try:
            async for text in self._connection:
                assert isinstance(text, str)
                try:
                    yield ReceiveMessage.validate_json(text)
                except ValidationError as exc:
                    log.error(f"Elevenlabs message unknown: {text}")
                    log.debug(f"Elevenlabs validation error: {exc.json()}")
                    yield None
        except (ConnectionClosed, CancelledError):
            log.info(f"Elevenlabs websocket connection closed.")
        finally:
            log.debug("Elevelabs.listen end")
