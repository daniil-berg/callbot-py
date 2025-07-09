from __future__ import annotations

from typing import Any, TYPE_CHECKING

from fastapi import status
from fastapi.exceptions import HTTPException

if TYPE_CHECKING:
    from callbot.functions import Function


__all__ = [
    "CallbotException",
    "EndCall",
]


class CallbotException(Exception):
    pass


class EndCall(CallbotException):
    pass


class CallManagerException(EndCall):
    def __init__(self, method: str, exception: Exception) -> None:
        super().__init__(f"Error in {method}: {exception}")


class TwilioStop(EndCall):
    def __init__(self) -> None:
        super().__init__("Twilio stop message received.")


class TwilioWebsocketDisconnect(EndCall):
    def __init__(self) -> None:
        super().__init__("Twilio websocket disconnected.")


class FunctionEndCall(EndCall):
    def __init__(self, function: Function[Any], detail: str) -> None:
        super().__init__(
            f"Function '{function.get_name()}' requested the call to end. "
            f"{detail}"
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
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JWT invalid",
        )


class JTIMissing(AuthException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JTI missing",
        )


class JTIReused(AuthException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JTI already used",
        )
