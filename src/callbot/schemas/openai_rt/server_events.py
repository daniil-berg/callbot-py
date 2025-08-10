from typing import Annotated, TypeAlias, Union, Literal

from openai.types.beta.realtime.conversation_item import ConversationItem as _ConversationItem
from openai.types.beta.realtime.conversation_item_content import ConversationItemContent as _ConversationItemContent
from openai.types.beta.realtime.conversation_item_created_event import ConversationItemCreatedEvent as _ConversationItemCreatedEvent
from openai.types.beta.realtime.conversation_item_input_audio_transcription_completed_event import ConversationItemInputAudioTranscriptionCompletedEvent
from openai.types.beta.realtime.conversation_item_input_audio_transcription_delta_event import ConversationItemInputAudioTranscriptionDeltaEvent
from openai.types.beta.realtime.conversation_item_input_audio_transcription_failed_event import ConversationItemInputAudioTranscriptionFailedEvent
from openai.types.beta.realtime.conversation_item_truncated_event import ConversationItemTruncatedEvent
from openai.types.beta.realtime.error_event import ErrorEvent
from openai.types.beta.realtime.input_audio_buffer_committed_event import InputAudioBufferCommittedEvent as _InputAudioBufferCommittedEvent
from openai.types.beta.realtime.input_audio_buffer_speech_started_event import InputAudioBufferSpeechStartedEvent
from openai.types.beta.realtime.input_audio_buffer_speech_stopped_event import InputAudioBufferSpeechStoppedEvent
from openai.types.beta.realtime.rate_limits_updated_event import RateLimitsUpdatedEvent
from openai.types.beta.realtime.realtime_response import RealtimeResponse as _RealtimeResponse
from openai.types.beta.realtime.response_audio_delta_event import ResponseAudioDeltaEvent
from openai.types.beta.realtime.response_audio_done_event import ResponseAudioDoneEvent
from openai.types.beta.realtime.response_audio_transcript_delta_event import ResponseAudioTranscriptDeltaEvent
from openai.types.beta.realtime.response_audio_transcript_done_event import ResponseAudioTranscriptDoneEvent
from openai.types.beta.realtime.response_content_part_added_event import ResponseContentPartAddedEvent
from openai.types.beta.realtime.response_content_part_done_event import ResponseContentPartDoneEvent
from openai.types.beta.realtime.response_created_event import ResponseCreatedEvent as _ResponseCreatedEvent
from openai.types.beta.realtime.response_done_event import ResponseDoneEvent as _ResponseDoneEvent
from openai.types.beta.realtime.response_function_call_arguments_delta_event import ResponseFunctionCallArgumentsDeltaEvent
from openai.types.beta.realtime.response_function_call_arguments_done_event import ResponseFunctionCallArgumentsDoneEvent
from openai.types.beta.realtime.response_output_item_added_event import ResponseOutputItemAddedEvent as _ResponseOutputItemAddedEvent
from openai.types.beta.realtime.response_output_item_done_event import ResponseOutputItemDoneEvent as _ResponseOutputItemDoneEvent
from openai.types.beta.realtime.session import Session as _Session
from openai.types.beta.realtime.session_created_event import SessionCreatedEvent
from openai.types.beta.realtime.session_updated_event import SessionUpdatedEvent as _SessionUpdatedEvent
from pydantic import Field, TypeAdapter

from callbot.settings._validators_types import Str128


class ConversationItemContent(_ConversationItemContent):
    # Was missing `audio`.
    type: Literal["input_text", "input_audio", "item_reference", "text", "audio"] | None = None  # type: ignore[assignment]


class ConversationItem(_ConversationItem):
    content: list[ConversationItemContent] | None = None  # type: ignore[assignment]
    # Was missing `in_progress`.
    status: Literal["completed", "incomplete", "in_progress"] | None = None  # type: ignore[assignment]


class ConversationItemCreatedEvent(_ConversationItemCreatedEvent):
    item: ConversationItem
    # Was missing `None`.
    previous_item_id: str | None  # type: ignore[assignment]


class InputAudioBufferCommittedEvent(_InputAudioBufferCommittedEvent):
    previous_item_id: str | None  # type: ignore[assignment]


class RealtimeResponse(_RealtimeResponse):
    output: list[ConversationItem] | None = None  # type: ignore[assignment]
    # Was missing `in_progress`.
    status: Literal["completed", "cancelled", "failed", "incomplete", "in_progress"] | None = None  # type: ignore[assignment]


class ResponseCreatedEvent(_ResponseCreatedEvent):
    response: RealtimeResponse


class ResponseDoneEvent(_ResponseDoneEvent):
    response: RealtimeResponse


class ResponseOutputItemAddedEvent(_ResponseOutputItemAddedEvent):
    item: ConversationItem


class ResponseOutputItemDoneEvent(_ResponseOutputItemDoneEvent):
    item: ConversationItem


class Session(_Session):
    instructions: Str128 | None = None


class SessionUpdatedEvent(_SessionUpdatedEvent):
    session: Session


# Incomplete!
AnyServerEvent: TypeAlias = Union[
    ConversationItemCreatedEvent,
    ConversationItemInputAudioTranscriptionCompletedEvent,
    ConversationItemInputAudioTranscriptionDeltaEvent,
    ConversationItemInputAudioTranscriptionFailedEvent,
    ConversationItemTruncatedEvent,
    ErrorEvent,
    InputAudioBufferCommittedEvent,
    InputAudioBufferSpeechStartedEvent,
    InputAudioBufferSpeechStoppedEvent,
    RateLimitsUpdatedEvent,
    ResponseAudioDeltaEvent,
    ResponseAudioDoneEvent,
    ResponseAudioTranscriptDeltaEvent,
    ResponseAudioTranscriptDoneEvent,
    ResponseContentPartAddedEvent,
    ResponseContentPartDoneEvent,
    ResponseCreatedEvent,
    ResponseDoneEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionCallArgumentsDoneEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    SessionCreatedEvent,
    SessionUpdatedEvent,
]
ServerEvent = TypeAdapter[AnyServerEvent](
    Annotated[
        AnyServerEvent,
        Field(discriminator="type"),
    ]
)
