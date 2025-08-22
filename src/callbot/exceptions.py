from __future__ import annotations

from typing import Any, TYPE_CHECKING

from fastapi import status
from fastapi.exceptions import HTTPException

if TYPE_CHECKING:
    from callbot.functions import Function
    from callbot.schemas.amd_status import AnsweredBy


__all__ = [
    "CallbotException",
    "EndCall",
]


class CallbotException(Exception):
    pass


class EndCall(CallbotException):
    pass


class EndCallInfo(EndCall):
    pass


class EndCallWarning(EndCall):
    pass


class EndCallError(EndCall):
    pass


class CallManagerException(EndCallError):
    def __init__(self, method: str, exception: Exception) -> None:
        super().__init__(f"Error in {method}: {exception}")


class SpeechStartTimeout(EndCallWarning):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"Speech has not started after {seconds} seconds.")


class TwilioStop(EndCallInfo):
    def __init__(self) -> None:
        super().__init__("Twilio stop message received.")


class TwilioWebsocketDisconnect(EndCallInfo):
    def __init__(self) -> None:
        super().__init__("Twilio websocket disconnected.")


class FunctionEndCall(EndCallInfo):
    def __init__(self, function: Function[Any], detail: str) -> None:
        super().__init__(
            f"Function '{function.get_name()}' requested the call to end. "
            f"{detail}"
        )


class AnsweringMachineDetected(EndCallInfo):
    def __init__(self, answered_by: AnsweredBy, time: float) -> None:
        super().__init__(
            f"Twilio detected {answered_by} after {time:.1f} seconds."
        )


class AuthException(HTTPException, CallbotException):
    def __init__(
        self,
        status_code: int,
        detail: object = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code, detail, headers)


class JWTInvalid(AuthException):
    def __init__(self, token: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"JWT invalid: {token}",
        )


class JTIMissing(AuthException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JTI missing from JWT payload",
        )


class JTIReused(AuthException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JTI already used",
        )
