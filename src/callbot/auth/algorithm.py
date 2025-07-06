from typing import Literal, TypeAlias


Algorithm: TypeAlias = Literal[
    "HS256",
    "HS384",
    "HS512",
    "ES256",
    "ES256K",
    "ES384",
    "ES512",
    "RS256",
    "RS384",
    "RS512",
    "PS256",
    "PS384",
    "PS512",
    "EdDSA",
]
DEFAULT_ALGORITHM: Literal["HS256"] = "HS256"
