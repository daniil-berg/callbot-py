from asyncio import Event, TaskGroup, gather, sleep, timeout
from dataclasses import dataclass, field
from string import Template as TemplateString
from typing import cast

from fastapi import WebSocket, WebSocketDisconnect, WebSocketException, status
from loguru import logger as log
from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection

from callbot.auth.jwt import JWT
from callbot.exceptions import (
    AuthException,
    CallManagerException,
    EndCall,
    FunctionEndCall,
    SpeechStartTimeout,
    TwilioStop,
    TwilioWebsocketDisconnect,
)
from callbot.functions import Function
from callbot.hooks import (
    AfterCallEndHook,
    AfterCallStartHook,
    AfterFunctionCallHook,
    BeforeConversationStartHook,
    BeforeFunctionCallHook,
)
from callbot.schemas.contact import Contact
from callbot.schemas.openai_rt.client_events import (  # type: ignore[attr-defined]
    ConversationItemCreateEvent as OpenAIRTConversationItemCreateEvent,
    ConversationItemTruncateEvent as OpenAIRTConversationItemTruncateEvent,
    InputAudioBufferAppendEvent as OpenAIRTInputAudioBufferAppendEvent,
    ResponseCreateEvent as OpenAIRTResponseCreateEvent,
    SessionUpdateEvent as OpenAIRTSessionUpdateEvent,
)
from callbot.schemas.openai_rt.server_events import (  # type: ignore[attr-defined]
    ConversationItemInputAudioTranscriptionCompletedEvent as OpenAIRTConversationItemInputAudioTranscriptionCompletedEvent,
    ConversationItemInputAudioTranscriptionDeltaEvent as OpenAIRTConversationItemInputAudioTranscriptionDeltaEvent,
    ErrorEvent as OpenAIRTErrorEvent,
    InputAudioBufferCommittedEvent as OpenAIRTInputAudioBufferCommittedEvent,
    InputAudioBufferSpeechStartedEvent as OpenAIRTInputAudioBufferSpeechStartedEvent,
    ResponseAudioDeltaEvent as OpenAIRTResponseAudioDeltaEvent,
    ResponseAudioDoneEvent as OpenAIRTResponseAudioDoneEvent,
    ResponseContentPartAddedEvent as OpenAIRTResponseContentPartAddedEvent,
    ResponseContentPartDoneEvent as OpenAIRTResponseContentPartDoneEvent,
    ResponseDoneEvent as OpenAIRTResponseDoneEvent,
    ServerEvent as OpenAIRTServerEvent,
)
from callbot.schemas.twilio_websocket_messages.inbound import (  # type: ignore[attr-defined]
    Connected as TwilioInboundConnected,
    Mark as TwilioInboundMark,
    Media as TwilioInboundMedia,
    Message as TwilioInboundMessage,
    Start as TwilioInboundStart,
    Stop as TwilioInboundStop,
)
from callbot.schemas.twilio_websocket_messages.outbound import (  # type: ignore[attr-defined]
    Clear as TwilioOutboundClear,
    Mark as TwilioOutboundMark,
    Media as TwilioOutboundMedia,
)
from callbot.settings import Settings


@dataclass
class CallManager:
    twilio_websocket: WebSocket
    openai_websocket: ClientConnection
    contact_info: Contact | None = field(default=None, init=False)
    contact_info_ready: Event = field(default_factory=Event, init=False)
    stream_sid: str = ""
    call_sid: str = ""
    conversation_ongoing: Event = field(default_factory=Event, init=False)
    latest_media_timestamp: int = 0
    last_assistant_item: str | None = None
    mark_queue: list[str] = field(default_factory=list)
    response_start_timestamp_twilio: int | None = None
    show_timing_math: bool = False
    transcript: dict[str, str] = field(default_factory=dict)

    async def openai_init_session(self) -> None:
        """
        Sends a `SessionUpdateEvent` message to the OpenAI websocket.

        The session instructions, temperature, voice, etc. are taken from the
        global settings object.
        """
        session_update = OpenAIRTSessionUpdateEvent(
            session=Settings().openai.session
        )
        log.debug("Updating OpenAI session")
        await self.openai_websocket.send(
            session_update.model_dump_json(exclude_none=True)
        )

    async def run(self) -> None:
        """
        Starts the main listen loops on the websocket connections.

        If an initial conversation prompt is configured, the model is prompted
        to start the conversation.
        """
        exceptions: ExceptionGroup | None = None
        try:
            async with TaskGroup() as task_group:
                task_group.create_task(self.openai_start_conversation())
                task_group.create_task(self.twilio_listen())
                task_group.create_task(self.openai_listen())
                task_group.create_task(self._timeout_loop())
        except* Exception as exc:
            exceptions = exc
            self._handle_run_exception(exc)
        finally:
            await self.twilio_websocket.close()
            await self.openai_websocket.close()
            await AfterCallEndHook(self, exceptions).dispatch()

    @classmethod
    def _handle_run_exception(cls, exc: ExceptionGroup) -> None:
        end_call_group, rest = exc.split(EndCall)
        if end_call_group:
            for exception in end_call_group.exceptions:
                cls._handle_end_call(exception)
        if rest is None:
            return
        auth_exception_group, rest = rest.split(AuthException)
        if auth_exception_group:
            # The Twilio listener is the only possible `AuthException` source.
            assert len(auth_exception_group.exceptions) == 1
            auth_exception = auth_exception_group.exceptions[0]
            # There should be no nested exception groups.
            assert isinstance(auth_exception, AuthException)
            # Propagate this as an appropriately coded websocket error.
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason=auth_exception.detail,
            ) from auth_exception
        if rest:
            log.exception(f"Unexpected exceptions in call: {rest}")

    @staticmethod
    def _handle_end_call(exc: EndCall | ExceptionGroup[EndCall]) -> None:
        msg = f"Call ended. {exc}"
        match exc:
            case FunctionEndCall() | TwilioStop() | TwilioWebsocketDisconnect():
                log.info(msg)
            case CallManagerException():
                log.exception(msg)
            case _:
                log.warning(msg)

    async def openai_start_conversation(self) -> None:
        """
        Prompts the model to start the conversation.

        If an initial conversation prompt is configured, this method sends a
        `ConversationItemCreateEvent` containing that user prompt, followed by
        a `ResponseCreateEvent`.
        """
        settings = Settings()
        if not (init_prompt := settings.openai.get_init_conversation_prompt()):
            return
        template = TemplateString(init_prompt)
        await self.contact_info_ready.wait()
        assert self.contact_info is not None
        prompt = template.safe_substitute(self.contact_info.model_dump())
        event = OpenAIRTConversationItemCreateEvent.with_user_prompt(prompt)
        await BeforeConversationStartHook(event.item, self).dispatch()
        await self.openai_send_conversation_item(event)

    async def openai_send_conversation_item(
        self,
        event: OpenAIRTConversationItemCreateEvent,
    ) -> None:
        """Sends the specified `event` followed by a `ResponseCreateEvent`."""
        await self.openai_websocket.send(
            event.model_dump_json(exclude_none=True)
        )
        await self.openai_websocket.send(
            OpenAIRTResponseCreateEvent().default_json()
        )

    async def twilio_listen(self) -> None:
        """
        Handles messages sent over the Twilio websocket.

        Each message is parsed via the Pydantic `Message` model union. See
        `handle_twilio_message` for details on how each type of message is
        handled. Closes the OpenAI websocket connection, if Twilio disconnects.
        """
        try:
            async for text in self.twilio_websocket.iter_text():
                await self.handle_twilio_message(text)
        except WebSocketDisconnect as e:
            raise TwilioWebsocketDisconnect() from e
        except EndCall as e:
            raise e
        except Exception as e:
            raise CallManagerException("twilio_listen", e) from e

    async def handle_twilio_message(self, text: str) -> None:
        try:
            message = TwilioInboundMessage.validate_json(text)
        except ValidationError as validation_error:
            log.error(f"Twilio message type unknown: {text}")
            log.debug(f"Twilio validation error: {validation_error.json()}")
            return
        match message:
            case TwilioInboundConnected():
                log.info(f"🔌 Connected to Twilio - {message}")
            case TwilioInboundStart():
                # TODO: Validate account and maybe stream SID!
                token = message.start.customParameters.get("token", "")
                _jwt = JWT.decode_and_invalidate(token)
                log.info(f"🔐 Connection secure")
                self.stream_sid = message.start.streamSid
                self.call_sid = message.start.callSid
                self.contact_info = Contact.model_validate(
                    message.start.customParameters
                )
                self.contact_info_ready.set()
                await AfterCallStartHook(self).dispatch()
                log.debug(f"Incoming stream has started {self.stream_sid}")
                self.response_start_timestamp_twilio = None
                self.latest_media_timestamp = 0
                self.last_assistant_item = None
            case TwilioInboundMedia():
                self.latest_media_timestamp = message.media.timestamp
                audio_append = OpenAIRTInputAudioBufferAppendEvent(
                    audio=message.media.payload,
                ).model_dump_json(exclude_none=True)
                # TODO: Handle `ConnectionClosed`.
                await self.openai_websocket.send(audio_append)
            case TwilioInboundMark():
                # If the last part an audio response by the bot has been played,
                # we clear the `conversation_ongoing` event. This means, the
                # `speech_start_timeout` clock will start ticking.
                if message.mark.name == "done":
                    log.debug("Bot has finished speaking")
                    self.conversation_ongoing.clear()
                # Conversely, if just a part of a response has been played,
                # we keep the event set to ensure no timeout occurs, while the
                # bot is "still speaking".
                else:
                    self.conversation_ongoing.set()
                if self.mark_queue:
                    self.mark_queue.pop(0)
            case TwilioInboundStop():
                raise TwilioStop()

    async def openai_listen(self) -> None:
        """
        Handles messages sent over the OpenAI websocket from their Realtime API.

        Each message is parsed via the Pydantic `ServerEvent` model union. See
        `handle_openai_event` for details on how each type of message is
        handled.
        """
        try:
            async for text in self.openai_websocket:
                assert isinstance(text, str)
                await self.handle_openai_event(text)
        except EndCall as e:
            raise e
        except Exception as e:
            raise CallManagerException("openai_listen", e) from e

    async def handle_openai_event(self, text: str) -> None:
        settings = Settings()
        try:
            event = OpenAIRTServerEvent.validate_json(text)
        except ValidationError as validation_error:
            log.error(f"OpenAI event unknown: {text}")
            log.debug(f"OpenAI validation error: {validation_error.json()}")
            return
        if event.type in settings.openai.log_event_types:
            log.debug(f"OpenAI event: {event.model_dump_json(exclude_defaults=True)}")
        match event:
            case OpenAIRTErrorEvent():
                error = event.error.model_dump_json(exclude_none=True)
                log.warning(f"OpenAI 'error' event: {error}")
            case OpenAIRTResponseContentPartAddedEvent():
                # Reserve a spot in the transcript log.
                self.transcript[event.item_id] = ""
            case OpenAIRTResponseContentPartDoneEvent():
                if event.part.type != "audio":
                    log.error("Response content part is not of type 'audio'")
                elif event.item_id not in self.transcript:
                    log.error("No item ID for response transcription")
                else:
                    transcript = f'Callbot: "{event.part.transcript}"'
                    self.transcript[event.item_id] = transcript
                    if settings.logging.transcript:
                        log.info(transcript)
            case OpenAIRTInputAudioBufferCommittedEvent():
                # Reserve a spot in the transcript log.
                self.transcript[event.item_id] = ""
            case OpenAIRTConversationItemInputAudioTranscriptionCompletedEvent():
                if event.item_id not in self.transcript:
                    log.error("No item ID for transcription")
                else:
                    transcript = f'Contact: "{event.transcript}"'
                    self.transcript[event.item_id] = transcript
                    if settings.logging.transcript:
                        log.info(transcript)
            case OpenAIRTResponseAudioDeltaEvent():
                twilio_media = TwilioOutboundMedia.with_payload(
                    payload=event.delta,
                    sid=self.stream_sid,
                ).model_dump_json()
                await self.twilio_websocket.send_text(twilio_media)
                if self.response_start_timestamp_twilio is None:
                    self.response_start_timestamp_twilio = self.latest_media_timestamp
                    if self.show_timing_math:
                        log.debug(f"Setting start timestamp for new response: {self.response_start_timestamp_twilio}ms")
                self.last_assistant_item = event.item_id
                await self._send_mark()
            case OpenAIRTResponseAudioDoneEvent():
                # We want to be notified by Twilio, when the last part of the
                # bot's audio response has been played.
                message = TwilioOutboundMark.with_name("done", self.stream_sid)
                await self.twilio_websocket.send_text(message.model_dump_json())
            case OpenAIRTInputAudioBufferSpeechStartedEvent():
                log.debug("Speech start detected.")
                # If speech is detected, we make sure the `conversation_ongoing`
                # event is set, so that a timeout cannot occur, while the other
                # side is speaking.
                self.conversation_ongoing.set()
                if self.last_assistant_item:
                    log.debug(f"Interrupting response with id: {self.last_assistant_item}")
                    await self._handle_speech_started_event()
            case OpenAIRTResponseDoneEvent():
                if not (function := Function.from_response(event.response)):
                    return
                await BeforeFunctionCallHook(function, self).dispatch()
                response_create = OpenAIRTResponseCreateEvent().default_json()
                exc, _ = await gather(
                    function(self),
                    self.openai_websocket.send(response_create),
                    return_exceptions=True,
                )
                await AfterFunctionCallHook(function, self, exc).dispatch()
                match exc:
                    case FunctionEndCall():
                        raise exc
                    case EndCall():
                        raise FunctionEndCall(function, str(exc)) from exc
                    case Exception():
                        log.warning(f"Error in '{function.get_name()}': {exc}")

    async def _handle_speech_started_event(self) -> None:
        log.debug("Handling speech started event.")
        if self.mark_queue and self.response_start_timestamp_twilio is not None:
            elapsed_time = self.latest_media_timestamp - self.response_start_timestamp_twilio
            if self.show_timing_math:
                log.debug(f"Calculating elapsed time for truncation: {self.latest_media_timestamp} - {self.response_start_timestamp_twilio} = {elapsed_time}ms")
            if self.last_assistant_item:
                if self.show_timing_math:
                    log.debug(f"Truncating item with ID: {self.last_assistant_item}, Truncated at: {elapsed_time}ms")
                conversation_item_trunc = OpenAIRTConversationItemTruncateEvent(
                    item_id=self.last_assistant_item,
                    content_index=0,
                    audio_end_ms=elapsed_time,
                ).model_dump_json(exclude_none=True)
                # TODO: Handle `ConnectionClosed`.
                await self.openai_websocket.send(conversation_item_trunc)
            await self.twilio_websocket.send_text(
                TwilioOutboundClear(streamSid=self.stream_sid).model_dump_json()
            )
            self.mark_queue.clear()
            self.last_assistant_item = None
            self.response_start_timestamp_twilio = None

    async def _send_mark(self) -> None:
        if not self.stream_sid:
            return
        mark = "responsePart"
        message = TwilioOutboundMark.with_name(mark, self.stream_sid)
        await self.twilio_websocket.send_text(message.model_dump_json())
        self.mark_queue.append(mark)

    async def _timeout_loop(self) -> None:
        settings = Settings()
        while True:
            seconds = settings.misc.speech_start_timeout
            try:
                async with timeout(seconds):
                    await gather(
                        sleep(1),  # Wait at least a second in each iteration.
                        self.conversation_ongoing.wait(),
                    )
            except TimeoutError as e:
                raise SpeechStartTimeout(cast(float, seconds)) from e
