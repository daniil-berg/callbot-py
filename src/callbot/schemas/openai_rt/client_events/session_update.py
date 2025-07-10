from typing import Literal

from openai.types.beta.realtime import session_update_event as base

from .session import Session


class SessionUpdateEvent(base.SessionUpdateEvent):
    session: Session
    type: Literal["session.update"] = "session.update"
