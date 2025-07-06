from fastapi import status
from fastapi.exceptions import HTTPException


class CallbotException(Exception):
    pass


class TwilioWebsocketStopReceived(CallbotException):
    pass


class EndCall(CallbotException):
    pass


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
