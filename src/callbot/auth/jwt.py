from typing import ClassVar, Self

from jwt.exceptions import DecodeError
from loguru import logger as log
from pydantic import ValidationError

from callbot.exceptions import JTIMissing, JTIReused, JWTInvalid
from callbot.settings import Settings
from .base_jwt import BaseJWT
from .payload import Payload


class JWT(BaseJWT[Payload]):
    used_jti: ClassVar[set[str]] = set()

    @classmethod
    def generate(cls) -> str:
        settings = Settings()
        jwt = cls(payload=Payload.generate())
        jwt.header.alg = settings.server.auth.alg
        return jwt.encode(key=settings.server.auth.secret)

    @classmethod
    def decode_and_invalidate(cls, token: str) -> Self:
        settings = Settings()
        try:
            jwt = super().decode(
                jwt=token,
                key=settings.server.auth.secret,
                algorithms=[settings.server.auth.alg],
                audience=settings.server.auth.aud,
                issuer=settings.server.auth.iss,
            )
        except (DecodeError, ValidationError):
            log.info("Invalid JWT")
            raise JWTInvalid from None
        if jwt.payload.registered_claims.jti is None:
            log.info("JTI missing from JWT payload")
            raise JTIMissing()
        if jwt.payload.registered_claims.jti in cls.used_jti:
            log.warning("Reused JTI encountered")
            raise JTIReused()
        cls.used_jti.add(jwt.payload.registered_claims.jti)
        return jwt
