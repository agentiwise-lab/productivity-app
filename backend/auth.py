"""Who is calling.

The backend derives ``user_id`` from a token it verified itself, never from
anything the client can simply assert. An ``X-User-Id`` header is exactly what
that rule forbids, so it exists only in dev mode and cannot be reached otherwise.

The mode is required rather than defaulted. A default would be a default of one
of two things: either dev, which ships an open door, or own, which breaks local
work in a way someone would "fix" by adding the header back. Making it explicit
costs one argument and removes both.

``own`` mode validates a token this service signed (``backend.tokens``). There is
no third party in the trust path any more: we mint the token at sign-in and we
verify it here.
"""

from __future__ import annotations

from typing import Callable, Literal

from fastapi import Header, HTTPException

from backend.tokens import TokenCodec, TokenInvalid

AuthMode = Literal["dev", "own"]


def build_current_user(
    mode: AuthMode, codec: TokenCodec | None = None
) -> Callable[..., str]:
    if mode == "dev":
        def current_user(x_user_id: str = Header(default="me")) -> str:
            return x_user_id

        return current_user

    if codec is None:
        raise ValueError("own auth mode requires a token codec")

    def current_user(authorization: str = Header(default="")) -> str:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        try:
            return codec.verify_access(token)
        except TokenInvalid:
            raise HTTPException(status_code=401, detail="invalid token")

    return current_user
