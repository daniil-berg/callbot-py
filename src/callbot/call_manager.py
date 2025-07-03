from asyncio import Event, gather
from dataclasses import dataclass, field
from string import Template as TemplateString

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from websockets.asyncio.client import ClientConnection

from callbot.exceptions import TwilioWebsocketStopReceived
from callbot.schemas.contact import Contact
from callbot.schemas.openai_rt.client_events import (  # type: ignore[attr-defined]
    ConversationItemCreateEvent as OpenAIRTConversationItemCreateEvent,
    ConversationItemTruncateEvent as OpenAIRTConversationItemTruncateEvent,
    InputAudioBufferAppendEvent as OpenAIRTInputAudioBufferAppendEvent,
    ResponseCreateEvent as OpenAIRTResponseCreateEvent,
    Session as OpenAIRTSession,
    SessionTurnDetection as OpenAIRTSessionTurnDetection,
    SessionUpdateEvent as OpenAIRTSessionUpdateEvent,
)
from callbot.schemas.openai_rt.function import Function
from callbot.schemas.openai_rt.server_events import (  # type: ignore[attr-defined]
    ErrorEvent as OpenAIRTErrorEvent,
    InputAudioBufferSpeechStartedEvent as OpenAIRTInputAudioBufferSpeechStartedEvent,
    ResponseAudioDeltaEvent as OpenAIRTResponseAudioDeltaEvent,
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


# TODO: Replace all `print` calls with proper logging.


@dataclass
class CallManager:
    twilio_websocket: WebSocket
    openai_websocket: ClientConnection
    contact_info: Contact | None = field(default=None, init=False)
    contact_info_ready: Event = field(default_factory=Event, init=False)
    stream_sid: str = ""
    call_sid: str = ""
    latest_media_timestamp: int = 0
    last_assistant_item: str | None = None
    mark_queue: list[str] = field(default_factory=list)
    response_start_timestamp_twilio: int | None = None
    show_timing_math: bool = False

    async def openai_init_session(self) -> None:
        """
        Sends a `SessionUpdateEvent` message to the OpenAI websocket.

        The session instructions, temperature, voice, etc. are taken from the
        global settings object.
        """
        session_update = OpenAIRTSessionUpdateEvent.from_settings()
        print("Updating OpenAI session")
        await self.openai_websocket.send(
            session_update.model_dump_json(exclude_none=True)
        )

    async def run(self) -> None:
        """
        Starts the main listen loops on the websocket connections.

        If an initial conversation prompt is configured, the model is prompted
        to start the conversation.
        """
        await gather(
            self.openai_start_conversation(),
            self.twilio_listen(),
            self.openai_listen(),
        )

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
        await self.openai_send_conversation_item(
            OpenAIRTConversationItemCreateEvent.with_user_prompt(prompt)
        )

    async def openai_send_conversation_item(
        self,
        event: OpenAIRTConversationItemCreateEvent,
    ) -> None:
        """Sends the specified `event` followed by a `ResponseCreateEvent`."""
        await self.openai_websocket.send(
            event.model_dump_json(exclude_none=True)
        )
        await self.openai_websocket.send(
            OpenAIRTResponseCreateEvent().model_dump_json(exclude_none=True)
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
        except (TwilioWebsocketStopReceived, WebSocketDisconnect):
            print("Twilio disconnected.")
            # TODO: Handle `ConnectionClosed`.
            await self.openai_websocket.close()

    async def handle_twilio_message(self, text: str) -> None:
        try:
            message = TwilioInboundMessage.validate_json(text)
        except ValidationError as validation_error:
            print(f"Twilio message type unknown: {text}")
            print(f"Twilio validation error: {validation_error.json()}")
            return
        match message:
            case TwilioInboundConnected():
                print(f"🔌 Connected to Twilio - {message}")
            case TwilioInboundStart():
                # TODO: Validate account and maybe stream SID!
                self.stream_sid = message.start.streamSid
                self.contact_info = Contact.model_validate(
                    message.start.customParameters
                )
                self.contact_info_ready.set()
                print(f"Incoming stream has started {self.stream_sid}")
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
                if self.mark_queue:
                    self.mark_queue.pop(0)
            case TwilioInboundStop():
                print(f"Call ended, stream {self.stream_sid} stopped")
                # TODO: Handle `ConnectionClosed`.
                await self.openai_websocket.close()
                await self.twilio_websocket.close()
                raise TwilioWebsocketStopReceived()

    async def openai_listen(self) -> None:
        """
        Handles messages sent over the OpenAI websocket from their Realtime API.

        Each message is parsed via the Pydantic `ServerEvent` model union. See
        `handle_openai_message` for details on how each type of message is
        handled.
        """
        try:
            async for text in self.openai_websocket:
                assert isinstance(text, str)
                await self.handle_openai_message(text)
        except Exception as e:
            print(f"Error in openai_listen: {e}")

    async def handle_openai_message(self, text: str) -> None:
        try:
            event = OpenAIRTServerEvent.validate_json(text)
        except ValidationError as validation_error:
            print(f"OpenAI event unknown: {text}")
            print(f"OpenAI validation error: {validation_error.json()}")
            return
        if event.type in Settings().openai.log_event_types:
            print(f"OpenAI event: {event.model_dump_json(exclude_defaults=True)}")
        match event:
            case OpenAIRTErrorEvent():
                error = event.error.model_dump_json(exclude_none=True)
                print(f"OpenAI 'error' event: {error}")
            case OpenAIRTResponseAudioDeltaEvent():
                twilio_media = TwilioOutboundMedia.with_payload(
                    payload=event.delta,
                    sid=self.stream_sid,
                ).model_dump_json()
                await self.twilio_websocket.send_text(twilio_media)
                if self.response_start_timestamp_twilio is None:
                    self.response_start_timestamp_twilio = self.latest_media_timestamp
                    if self.show_timing_math:
                        print(f"Setting start timestamp for new response: {self.response_start_timestamp_twilio}ms")
                self.last_assistant_item = event.item_id
                await self._send_mark()
            case OpenAIRTInputAudioBufferSpeechStartedEvent():
                # Trigger an interruption. Alternatively `input_audio_buffer.speech_stopped` or both may work.
                print("Speech started detected.")
                if self.last_assistant_item:
                    print(f"Interrupting response with id: {self.last_assistant_item}")
                    await self._handle_speech_started_event()
            case OpenAIRTResponseDoneEvent():
                if not (function := Function.from_response(event.response)):
                    return
                response_create = OpenAIRTResponseCreateEvent()
                exc, _ = await gather(
                    function(self),
                    self.openai_websocket.send(
                        response_create.model_dump_json(exclude_none=True)
                    ),
                    return_exceptions=True,
                )
                if isinstance(exc, BaseException):
                    print(f"Error in function '{function.get_name()}': {exc}")

    async def _handle_speech_started_event(self) -> None:
        print("Handling speech started event.")
        if self.mark_queue and self.response_start_timestamp_twilio is not None:
            elapsed_time = self.latest_media_timestamp - self.response_start_timestamp_twilio
            if self.show_timing_math:
                print(f"Calculating elapsed time for truncation: {self.latest_media_timestamp} - {self.response_start_timestamp_twilio} = {elapsed_time}ms")
            if self.last_assistant_item:
                if self.show_timing_math:
                    print(f"Truncating item with ID: {self.last_assistant_item}, Truncated at: {elapsed_time}ms")
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
