from __future__ import annotations

from asyncio import create_task, gather
from string import Template
from types import TracebackType
from typing import Self, TYPE_CHECKING

from loguru import logger as log
from pydantic import ValidationError
# TODO: Migrate to httpx-ws
from websockets.asyncio.client import ClientConnection, connect

from callbot.backends import Backend
from callbot.exceptions import EndCall, CallManagerException, FunctionEndCall
from callbot.functions import Function
from callbot.hooks import BeforeFunctionCallHook, AfterFunctionCallHook
from callbot.schemas.openai_rt.client_events import (  # type: ignore[attr-defined]
    ConversationItemCreateEvent,
    ConversationItemTruncateEvent,
    InputAudioBufferAppendEvent,
    ResponseCreateEvent,
    SessionUpdateEvent,
)
from callbot.schemas.openai_rt.server_events import (  # type: ignore[attr-defined]
    ConversationItemInputAudioTranscriptionCompletedEvent,
    ErrorEvent,
    InputAudioBufferCommittedEvent,
    InputAudioBufferSpeechStartedEvent,
    ResponseAudioDeltaEvent,
    ResponseAudioDoneEvent,
    ResponseContentPartAddedEvent,
    ResponseContentPartDoneEvent,
    ResponseDoneEvent,
    ServerEvent,
)
from callbot.settings import Settings

if TYPE_CHECKING:
    from callbot.call_manager import CallManager


class OpenAIBackend(Backend):
    """
    Reference implementation of a conversation backend powered by OpenAI.

    Uses the OpenAI Realtime API for direct speech-to-speech conversation.
    """

    _websocket: connect
    _connection: ClientConnection
    _last_response_item: str | None
    _response_start_timestamp: int | None
    _transcript: dict[str, str]

    def __init__(self):
        super().__init__()
        settings = Settings()
        self._websocket = connect(
            uri=settings.openai.realtime_stream_url,
            additional_headers=settings.openai.get_realtime_auth_headers(),
        )
        self._last_response_item = None
        self._response_start_timestamp = None
        self._transcript = {}

    async def __aenter__(self) -> Self:
        """Allows usage of a client instance as an `async` context manager."""
        self._connection = await self._websocket.__aenter__()
        return self

    async def __aexit__[E: BaseException](
        self,
        exc_type: type[E] | None,
        exc_val: E | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exits the `async with`-block."""
        await self._connection.__aexit__(exc_type, exc_val, exc_tb)

    async def init_session(self) -> None:
        """
        Sends a `SessionUpdateEvent` message to the OpenAI websocket.

        The session instructions, temperature, voice, etc. are taken from the
        global settings object.
        """
        session_update = SessionUpdateEvent(
            session=Settings().openai.session
        )
        log.debug("Updating OpenAI session")
        await self._connection.send(
            session_update.model_dump_json(exclude_none=True)
        )

    async def listen(self, call_manager: CallManager) -> None:
        """
        Handles messages sent over the OpenAI websocket from their Realtime API.

        Each message is parsed via the Pydantic `ServerEvent` model union. See
        `handle_openai_event` for details on how each type of message is
        handled.
        """
        start_conversation_task = create_task(self._start_conversation())
        try:
            async for text in self._connection:
                assert isinstance(text, str)
                await self._handle_event(text, call_manager)
        except EndCall as e:
            raise e
        except Exception as e:
            raise CallManagerException("OpenAIBackend.listen", e) from e
        finally:
            await start_conversation_task

    async def _start_conversation(self) -> None:
        """
        Prompts the model to start the conversation.

        If an initial conversation prompt is configured, this method sends a
        `ConversationItemCreateEvent` containing that user prompt, followed by
        a `ResponseCreateEvent`.
        """
        settings = Settings()
        if not (init_prompt := settings.openai.get_init_conversation_prompt()):
            return
        template = Template(init_prompt)
        contact = await self.get_contact_info_when_ready()
        prompt = template.safe_substitute(contact.model_dump())
        event = ConversationItemCreateEvent.with_user_prompt(prompt)
        await self._send_conversation_item(event)

    async def _send_conversation_item(
        self,
        event: ConversationItemCreateEvent,
    ) -> None:
        """Sends the specified `event` followed by a `ResponseCreateEvent`."""
        await self._connection.send(
            event.model_dump_json(exclude_none=True)
        )
        await self._connection.send(
            ResponseCreateEvent().default_json()
        )

    async def _handle_event(self, text: str, call_manager: CallManager) -> None:
        settings = Settings()
        try:
            event = ServerEvent.validate_json(text)
        except ValidationError as validation_error:
            log.error(f"OpenAI event unknown: {text}")
            log.debug(f"OpenAI validation error: {validation_error.json()}")
            return
        if event.type in settings.openai.log_event_types:
            log.debug(f"OpenAI event: {event.model_dump_json(exclude_defaults=True)}")
        match event:
            case ErrorEvent():
                error = event.error.model_dump_json(exclude_none=True)
                log.warning(f"OpenAI 'error' event: {error}")
            case ResponseContentPartAddedEvent():
                # Reserve a spot in the transcript log.
                self._transcript[event.item_id] = ""
            case ResponseContentPartDoneEvent():
                if event.part.type != "audio":
                    log.error("Response content part is not of type 'audio'")
                elif event.item_id not in self._transcript:
                    log.error("No item ID for response transcription")
                else:
                    transcript = f'Callbot: "{event.part.transcript}"'
                    self._transcript[event.item_id] = transcript
                    if settings.logging.transcript:
                        log.info(transcript)
            case InputAudioBufferCommittedEvent():
                # Reserve a spot in the transcript log.
                self._transcript[event.item_id] = ""
            case ConversationItemInputAudioTranscriptionCompletedEvent():
                if event.item_id not in self._transcript:
                    log.error("No item ID for transcription")
                else:
                    transcript = f'Contact: "{event.transcript}"'
                    self._transcript[event.item_id] = transcript
                    if settings.logging.transcript:
                        log.info(transcript)
            case ResponseAudioDeltaEvent():
                await call_manager.send_media(event.delta)
                if self._response_start_timestamp is None:
                    self._response_start_timestamp = call_manager.latest_media_timestamp
                self._last_response_item = event.item_id
                await call_manager.send_response_part_mark()
            case ResponseAudioDoneEvent():
                # We want to be notified by Twilio, when the last part of the
                # bot's audio response has been played.
                await call_manager.send_response_done_mark()
            case InputAudioBufferSpeechStartedEvent():
                log.debug("Speech start detected.")
                # If speech is detected, we make sure the `conversation_ongoing`
                # event is set, so that a timeout cannot occur, while the other
                # side is speaking.
                call_manager.conversation_ongoing.set()
                await self._handle_speech_started(call_manager)
            case ResponseDoneEvent():
                if not (function := Function.from_response(event.response)):
                    return
                await self._handle_function_call(function, call_manager)

    async def _handle_speech_started(self, call_manager: CallManager) -> None:
        if not call_manager.mark_queue or self._response_start_timestamp is None:
            return
        log.debug("Handling speech started event.")
        # TODO: This tends to cause an OpenAI error event. Fix this.
        #       https://platform.openai.com/docs/api-reference/realtime_client_events/conversation/item/truncate#realtime_client_events/conversation/item/truncate-audio_end_ms
        elapsed_time = call_manager.latest_media_timestamp - self._response_start_timestamp
        if self._last_response_item:
            log.debug(f"Interrupting response: {self._last_response_item}")
            conversation_item_trunc = ConversationItemTruncateEvent(
                item_id=self._last_response_item,
                content_index=0,
                audio_end_ms=elapsed_time,
            ).model_dump_json(exclude_none=True)
            await self._connection.send(conversation_item_trunc)
        await call_manager.clear_marks()
        self._last_response_item = None
        self._response_start_timestamp = None

    async def _handle_function_call(
        self,
        function: Function,
        call_manager: CallManager,
    ) -> None:
        await BeforeFunctionCallHook(function, call_manager).dispatch()
        response_create = ResponseCreateEvent().default_json()
        exc, _ = await gather(
            function(call_manager),
            self._connection.send(response_create),
            return_exceptions=True,
        )
        await AfterFunctionCallHook(function, call_manager, exc).dispatch()
        match exc:
            case FunctionEndCall():
                raise exc
            case EndCall():
                raise FunctionEndCall(function, str(exc)) from exc
            case Exception():
                log.warning(f"Error in '{function.get_name()}': {exc}")

    async def send_audio(self, payload: str) -> None:
        audio_append = InputAudioBufferAppendEvent(
            audio=payload,
        ).model_dump_json(exclude_none=True)
        await self._connection.send(audio_append)

    def get_transcript(self) -> str:
        return "\n".join(self._transcript.values())
