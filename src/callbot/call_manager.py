from asyncio import Event, Queue, TaskGroup, gather, sleep, timeout
from dataclasses import dataclass, field
from typing import ClassVar, Self, cast

from fastapi import WebSocket, WebSocketDisconnect, WebSocketException, status
from loguru import logger as log
from pydantic import ValidationError

from callbot.auth.jwt import JWT
from callbot.backends import Backend
from callbot.exceptions import (
    AnsweringMachineDetected,
    AuthException,
    CallManagerException,
    CallbotException,
    EndCall,
    EndCallError,
    EndCallInfo,
    SpeechStartTimeout,
    TwilioStop,
    TwilioWebsocketDisconnect,
)
from callbot.hooks import (
    AfterCallEndHook,
    AfterCallStartHook,
)
from callbot.schemas.amd_status import AMDStatus
from callbot.schemas.contact import Contact
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
    _active_instances: ClassVar[dict[str, Self]] = {}

    backend: Backend
    twilio_websocket: WebSocket
    stream_sid: str = ""
    call_sid: str = ""
    conversation_ongoing: Event = field(default_factory=Event, init=False)
    latest_media_timestamp: int = 0
    mark_queue: list[str] = field(default_factory=list)
    transcript: dict[str, str] = field(default_factory=dict)

    _abort_exception: Queue[CallbotException] = field(
        default_factory=lambda: Queue(maxsize=1),
        init=False,
    )

    @classmethod
    def get(cls, call_sid: str) -> Self | None:
        return cls._active_instances.get(call_sid)

    async def run(self) -> None:
        """
        Starts the main listen loops on the websocket connections.

        If an initial conversation prompt is configured, the model is prompted
        to start the conversation.
        """
        await self.backend.init_session()
        exceptions: ExceptionGroup | None = None
        try:
            async with TaskGroup() as task_group:
                task_group.create_task(self.twilio_listen())
                task_group.create_task(self.backend.listen(self))
                task_group.create_task(self._timeout_loop())
                task_group.create_task(self._abort_wait())
        except* Exception as exc:
            exceptions = exc
            self._handle_run_exception(exc)
        finally:
            await self.twilio_websocket.close()
            await AfterCallEndHook(self, exceptions).dispatch()
            self._active_instances.pop(self.call_sid, None)

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
            case EndCallInfo():
                log.info(msg)
            case EndCallError():
                log.exception(msg)
            case _:
                log.warning(msg)

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
                self._active_instances[self.call_sid] = self
                self.backend.contact_info = Contact.model_validate(
                    message.start.customParameters
                )
                await AfterCallStartHook(self).dispatch()
                log.debug(f"Incoming stream has started {self.stream_sid}")
            case TwilioInboundMedia():
                self.latest_media_timestamp = message.media.timestamp
                await self.backend.send_audio(message.media.payload)
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

    async def send_media(self, payload: str) -> None:
        twilio_media = TwilioOutboundMedia.with_payload(
            payload=payload,
            sid=self.stream_sid,
        ).model_dump_json()
        await self.twilio_websocket.send_text(twilio_media)

    async def send_response_done_mark(self) -> None:
        message = TwilioOutboundMark.with_name("done", self.stream_sid)
        await self.twilio_websocket.send_text(message.model_dump_json())

    async def send_response_part_mark(self) -> None:
        if not self.stream_sid:
            return
        mark = "responsePart"
        message = TwilioOutboundMark.with_name(mark, self.stream_sid)
        await self.twilio_websocket.send_text(message.model_dump_json())
        self.mark_queue.append(mark)

    async def clear_marks(self) -> None:
        await self.twilio_websocket.send_text(
            TwilioOutboundClear(streamSid=self.stream_sid).model_dump_json()
        )
        self.mark_queue.clear()

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

    async def _abort_wait(self) -> None:
        exception = await self._abort_exception.get()
        raise exception

    def _abort(self, exception: CallbotException) -> None:
        self._abort_exception.put_nowait(exception)

    def answering_machine_detected(self, amd_status: AMDStatus) -> None:
        self._abort(AnsweringMachineDetected(
            answered_by=amd_status.answered_by,
            time=amd_status.machine_detection_duration * 1000,
        ))
