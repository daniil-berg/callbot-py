from collections.abc import Iterable
from datetime import timedelta
from json import JSONEncoder
from typing import Any, ClassVar, Self, cast

from jwt import decode_complete, encode
from pydantic import BaseModel

from callbot.types import StrDict
from .base_payload import BasePayload
from .header import Header


class BaseJWT[PayloadT: BasePayload](BaseModel):
    _payload_model: ClassVar[Any] = None

    header: Header = Header()
    payload: PayloadT
    signature: str | bytes | None = None

    def encode(
        self,
        key: str | bytes = "",
        json_encoder: type[JSONEncoder] | None = None,
        sort_headers: bool = True,
    ) -> str:
        # The `algorithm` argument is redundant, when `alg` is in the header.
        return encode(
            payload=self.payload.dump_claims() if self.payload else {},
            key=key,
            headers=self.header.model_dump(),
            json_encoder=json_encoder,
            sort_headers=sort_headers,
        )

    @classmethod
    def decode(
        cls,
        jwt: str | bytes,
        key: str | bytes = "",
        algorithms: list[str] | None = None,
        options: StrDict | None = None,
        detached_payload: bytes | None = None,
        audience: str | Iterable[str] | None = None,
        issuer: str | None = None,
        leeway: float | timedelta = 0,
    ) -> Self:
        decoded = decode_complete(
            jwt=jwt,
            key=key,
            algorithms=algorithms,
            options=options,
            detached_payload=detached_payload,
            audience=audience,
            issuer=issuer,
            leeway=leeway,
        )
        header = Header.model_validate(decoded["header"])
        payload_model = cls._get_payload_model()
        payload = payload_model.from_claims(decoded["payload"])
        if isinstance(jwt, str):
            signature = jwt.rsplit(".", 1)[1]
        else:
            signature = decoded["signature"]
        return cls(header=header, payload=payload, signature=signature)

    @classmethod
    def model_parametrized_name(cls, params: tuple[type[Any], ...]) -> str:
        for param in params:
            if issubclass(param, BasePayload):
                cls._payload_model = param
        return super().model_parametrized_name(params)

    @classmethod
    def _get_payload_model(cls) -> type[PayloadT]:
        if cls._payload_model is None:
            raise AttributeError("Payload model is not set")
        return cast(type[PayloadT], cls._payload_model)
