from typing import Any, Self

from pydantic import BaseModel

from callbot.types import StrDict
from .base_claims import BaseClaims
from .registered_claims import RegisteredClaims


class BasePayload(BaseModel):
    registered_claims: RegisteredClaims = RegisteredClaims()
    public_claims: BaseClaims = BaseClaims()

    def dump_claims(self) -> dict[str, Any]:
        claims = self.registered_claims.model_dump(exclude_unset=True)
        claims.update(self.public_claims.model_dump(exclude_unset=True))
        return claims

    @classmethod
    def from_claims(cls, claims: StrDict) -> Self:
        registered_claims = {
            key: claims.pop(key)
            for key in RegisteredClaims.model_fields.keys()
            if key in claims
        }
        return cls.model_validate({
            "registered_claims": registered_claims,
            "public_claims": claims,
        })
