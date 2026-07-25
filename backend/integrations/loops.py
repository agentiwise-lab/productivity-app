"""Sending the OTP email through Loops.

A thin wrapper over Loops' transactional endpoint, ported from ad_analytics but
made synchronous: the routes here are sync ``def`` and FastAPI runs them in a
threadpool, so a blocking send costs a worker thread, not the event loop.

When Loops is not configured the service does not fail: it logs the code, so
signup is fully testable on localhost with no email account at all. That is the
same choice ad_analytics makes, and it is what lets the whole auth flow run
before any secret is set.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

LOOPS_TRANSACTIONAL_URL = "https://app.loops.so/api/v1/transactional"


class LoopsEmailService:
    def __init__(self, api_key: str | None, otp_transactional_id: str | None) -> None:
        self._api_key = api_key
        self._transactional_id = otp_transactional_id
        self._enabled = bool(api_key and otp_transactional_id)

    def send_otp(self, email: str, code: str) -> None:
        if not self._enabled:
            # Dev path: no Loops, so the code goes to the log rather than nowhere.
            log.warning("LOOPS not configured; OTP for %s is %s (dev only)", email, code)
            return

        payload: dict[str, Any] = {
            "email": email,
            "transactionalId": self._transactional_id,
            "dataVariables": {"otp": code},
        }
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    LOOPS_TRANSACTIONAL_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
            if response.status_code >= 400:
                # A failed send is logged, not raised: the OTP is already stored,
                # and surfacing the provider's 5xx to the user as a signup error
                # would be blaming them for our mail vendor.
                log.warning(
                    "Loops send failed %s: %s", response.status_code, response.text[:300]
                )
        except Exception:
            log.exception("Loops send raised for %s", email)


class FakeEmailService:
    """Captures codes instead of sending them, so tests can read the OTP the
    service generated without any network."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_otp(self, email: str, code: str) -> None:
        self.sent.append((email, code))

    def last_code(self, email: str) -> str | None:
        for sent_email, code in reversed(self.sent):
            if sent_email == email:
                return code
        return None
