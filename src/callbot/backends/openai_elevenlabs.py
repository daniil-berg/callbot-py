# TODO: Move this and related settings to a plugin.

from __future__ import annotations

from asyncio import TaskGroup
from types import TracebackType
from typing import Self, TYPE_CHECKING

from loguru import logger as log

from callbot.backends._elevenlabs import Elevenlabs
from callbot.backends.openai import OpenAIBackend
from callbot.schemas.elevenlabs.receive import (
    AnyReceiveMessage,
    AudioOutputMulti,
    FinalOutputMulti,
)
from callbot.schemas.openai_rt.server_events import (
    AnyServerEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
)
from callbot.settings import Settings

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class OpenAIElevenLabsBackend(OpenAIBackend):
    _elevenlabs: Elevenlabs

    async def __aenter__(self) -> Self:
        await super().__aenter__()
        self._elevenlabs = await Elevenlabs().__aenter__()
        return self

    async def __aexit__[E: BaseException](
        self,
        exc_type: type[E] | None,
        exc_val: E | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._elevenlabs.__aexit__(exc_type, exc_val, exc_tb)
        await super().__aexit__(exc_type, exc_val, exc_tb)

    async def listen(self, call_manager: CallManager) -> None:
        try:
            async with TaskGroup() as task_group:
                task_group.create_task(super().listen(call_manager))
                task_group.create_task(self._listen_elevenlabs(call_manager))
        finally:
            log.debug("OpenAIElevenLabsBackend.listen end")

    async def _listen_elevenlabs(self, call_manager: CallManager) -> None:
        async for message in self._elevenlabs.listen():
            await self._handle_elevenlabs_message(message, call_manager)

    async def _handle_elevenlabs_message(
        self,
        message: AnyReceiveMessage,
        call_manager: CallManager,
    ) -> None:
        match message:
            case AudioOutputMulti():
                log.debug(
                    f"Received Elevenlabs audio for context: "
                    f"{message.context_id}"
                )
                await call_manager.send_media(message.audio)
                if self._response_start_timestamp is None:
                    self._response_start_timestamp = call_manager.latest_media_timestamp
                await call_manager.send_response_part_mark()
            case FinalOutputMulti():
                log.debug(
                    f"Received final audio for Elevenlabs context: "
                    f"{message.context_id}"
                )
                # We want to be notified by Twilio, when the last part of the
                # bot's audio response has been played.
                await call_manager.send_response_done_mark()

    async def _handle_event(
        self,
        event: AnyServerEvent,
        call_manager: CallManager,
    ) -> None:
        settings = Settings()
        assert settings.openai.session.modalities == ("text", )
        match event:
            case ResponseTextDeltaEvent():
                self._last_response_item = event.item_id
                await self._elevenlabs.send_text(
                    event.delta,
                    context_id=event.item_id,
                )
            case ResponseTextDoneEvent():
                await self._elevenlabs.flush_context(event.item_id)
                await self._elevenlabs.close_context(event.item_id)
            case _:
                await super()._handle_event(event, call_manager)

    async def _handle_speech_started(self, call_manager: CallManager) -> None:
        if not call_manager.mark_queue or self._response_start_timestamp is None:
            return
        log.debug("Handling speech started event.")
        if self._last_response_item:
            log.debug(f"Interrupting response: {self._last_response_item}")
            await self._elevenlabs.close_context(self._last_response_item)
        await call_manager.clear_marks()
        self._last_response_item = None
        self._response_start_timestamp = None
