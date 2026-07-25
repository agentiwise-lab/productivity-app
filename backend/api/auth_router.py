"""HTTP surface for the auth flow.

Thin, like every route in this codebase: parse a small body, call one
``AuthService`` method, and translate its typed error into a status code. No
logic lives here. The only judgement in the file is which failure maps to which
code, and that mapping is the whole point of the service raising distinct
exceptions instead of returning a bool.

Password reset answers 200 whether or not the address exists, so the endpoint
cannot be used to discover who has an account. Signup is the deliberate
exception: it tells a known user to sign in instead, because the product needs
that message.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.models.auth import OtpPurpose, TokenPair
from backend.services.auth_service import (
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
    OtpExpired,
    OtpLockedOut,
    OtpMismatch,
    OtpNotFound,
    RefreshInvalid,
    RefreshReused,
    ResendTooSoon,
)


class OtpSendBody(BaseModel):
    email: str
    purpose: OtpPurpose = OtpPurpose.SIGNUP


class OtpVerifyBody(BaseModel):
    email: str
    code: str
    purpose: OtpPurpose = OtpPurpose.SIGNUP


class RegisterBody(BaseModel):
    email: str
    code: str
    password: str = Field(min_length=8)


class LoginBody(BaseModel):
    email: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class ResetRequestBody(BaseModel):
    email: str


class ResetConfirmBody(BaseModel):
    email: str
    code: str
    new_password: str = Field(min_length=8)


class MessageOut(BaseModel):
    message: str


def build_auth_router(auth: AuthService) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/otp/send", response_model=MessageOut)
    def send_otp(body: OtpSendBody) -> MessageOut:
        try:
            auth.send_otp(body.email, body.purpose)
        except EmailAlreadyRegistered:
            raise HTTPException(409, "This email is already registered. Please sign in.")
        except ResendTooSoon as error:
            raise HTTPException(
                429, f"Please wait {error.retry_after}s before requesting another code."
            )
        return MessageOut(message="If the email is valid, a code is on its way.")

    @router.post("/otp/verify", response_model=MessageOut)
    def verify_otp(body: OtpVerifyBody) -> MessageOut:
        try:
            auth.verify_otp(body.email, body.purpose, body.code)
        except OtpLockedOut:
            raise HTTPException(429, "Too many attempts. Request a new code.")
        except (OtpNotFound, OtpExpired, OtpMismatch) as error:
            raise HTTPException(400, _otp_message(error))
        return MessageOut(message="Verified.")

    @router.post("/register", response_model=TokenPair, status_code=201)
    def register(body: RegisterBody) -> TokenPair:
        try:
            return auth.register(body.email, body.code, body.password)
        except EmailAlreadyRegistered:
            raise HTTPException(409, "This email is already registered. Please sign in.")
        except OtpLockedOut:
            raise HTTPException(429, "Too many attempts. Request a new code.")
        except (OtpNotFound, OtpExpired, OtpMismatch) as error:
            raise HTTPException(400, _otp_message(error))

    @router.post("/login", response_model=TokenPair)
    def login(body: LoginBody) -> TokenPair:
        try:
            return auth.authenticate(body.email, body.password)
        except InvalidCredentials:
            raise HTTPException(401, "Incorrect email or password.")

    @router.post("/refresh", response_model=TokenPair)
    def refresh(body: RefreshBody) -> TokenPair:
        try:
            return auth.refresh(body.refresh_token)
        except (RefreshInvalid, RefreshReused):
            raise HTTPException(401, "Session expired. Sign in again.")

    @router.post("/logout", status_code=204)
    def logout(body: RefreshBody) -> None:
        auth.revoke(body.refresh_token)

    @router.post("/password/reset/request", response_model=MessageOut)
    def reset_request(body: ResetRequestBody) -> MessageOut:
        # Always 200: whether or not the address exists is not ours to reveal.
        auth.send_otp(body.email, OtpPurpose.RESET)
        return MessageOut(message="If the email is registered, a reset code is on its way.")

    @router.post("/password/reset/confirm", response_model=MessageOut)
    def reset_confirm(body: ResetConfirmBody) -> MessageOut:
        try:
            auth.reset_password(body.email, body.code, body.new_password)
        except OtpLockedOut:
            raise HTTPException(429, "Too many attempts. Request a new code.")
        except (OtpNotFound, OtpExpired, OtpMismatch, InvalidCredentials) as error:
            raise HTTPException(400, _otp_message(error))
        return MessageOut(message="Password updated.")

    return router


def _otp_message(error: Exception) -> str:
    if isinstance(error, OtpMismatch):
        return f"Incorrect code. {error.remaining} attempt(s) left."
    if isinstance(error, OtpExpired):
        return "That code has expired. Request a new one."
    if isinstance(error, OtpNotFound):
        return "No code found for this email. Request a new one."
    return "Could not verify the code."
