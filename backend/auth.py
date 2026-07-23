"""Who is calling.

Plan 6.5: the backend derives ``user_id`` from a verified Supabase JWT and never
from anything the client can simply assert. An ``X-User-Id`` header is exactly
what that rule forbids, so it exists only in dev mode and cannot be reached
otherwise.

The mode is required rather than defaulted. A default would be a default of one
of two things: either dev, which ships an open door, or supabase, which breaks
local work in a way someone would "fix" by adding the header back. Making it
explicit costs one argument and removes both.
"""

from __future__ import annotations

from typing import Callable, Literal

import jwt
from fastapi import Header, HTTPException

AuthMode = Literal["dev", "supabase"]


def build_current_user(
    mode: AuthMode, jwt_secret: str | None = None
) -> Callable[..., str]:
    if mode == "dev":
        def current_user(x_user_id: str = Header(default="me")) -> str:
            return x_user_id

        return current_user

    if not jwt_secret:
        raise ValueError("supabase auth mode requires a JWT secret")

    def current_user(authorization: str = Header(default="")) -> str:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="missing bearer token")
        try:
            claims = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="invalid token")

        subject = claims.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="token has no subject")
        return subject

    return current_user
