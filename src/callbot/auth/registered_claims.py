from .base_claims import BaseClaims


class RegisteredClaims(BaseClaims):
    iss: str | None = None
    sub: str | None = None
    aud: str | None = None
    exp: int | None = None
    nbf: int | None = None
    iat: int | None = None
    jti: str | None = None
