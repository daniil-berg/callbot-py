from time import time
from typing import Self
from uuid import uuid4

from callbot.settings import Settings
from .base_payload import BasePayload
from .public_claims import PublicClaims
from .registered_claims import RegisteredClaims


class Payload(BasePayload):
    public_claims: PublicClaims = PublicClaims()

    @classmethod
    def generate(cls) -> Self:
        settings = Settings()
        now = int(time())
        registered_claims = RegisteredClaims(
            iat=now,
            nbf=now,
            jti=str(uuid4()),
            exp=now + settings.server.auth.expiration_seconds,
        )
        if settings.server.auth.iss:
            registered_claims.iss = settings.server.auth.iss
        if settings.server.auth.aud:
            registered_claims.aud = settings.server.auth.aud
        public_claims = PublicClaims()
        return cls(
            registered_claims=registered_claims,
            public_claims=public_claims,
        )
