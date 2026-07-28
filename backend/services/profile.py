"""Reading and setting the user's display name.

Kept apart from the auth service on purpose: authenticating and being called
something are different jobs, and the auth contract has no business growing a
profile method. This one leans on the same credentials repository (the ``users``
row is where the name lives) but exposes only the safe, name-shaped view.
"""

from __future__ import annotations

from typing import Protocol

from backend.models.profile import Profile
from backend.services.notifications import NotifyLevel


class CredentialsRepositoryLike(Protocol):
    def get_user_by_id(self, user_id: str):
        ...

    def set_name(self, user_id: str, name: str | None) -> None:
        ...

    def set_notify_level(self, user_id: str, level: str) -> None:
        ...


class UserNotFound(Exception):
    """The token named a user that no longer exists. The route turns this into a
    404 rather than inventing an empty profile."""


class ProfileService(Protocol):
    def get(self, user_id: str) -> Profile:
        ...

    def set_name(self, user_id: str, name: str | None) -> Profile:
        ...

    def set_notify_level(self, user_id: str, level: str) -> Profile:
        ...


#: A display name is a label, not prose. Long enough for a real name, short
#: enough that the greeting and the You row never have to wrap.
_MAX_NAME = 80


class DefaultProfileService:
    def __init__(self, repo: CredentialsRepositoryLike) -> None:
        self._repo = repo

    def get(self, user_id: str) -> Profile:
        user = self._repo.get_user_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return Profile(
            email=user.email, name=user.name, notify_level=user.notify_level
        )

    def set_notify_level(self, user_id: str, level: str) -> Profile:
        """Validate here, not only at the database.

        The column carries a check constraint, so an unknown value would fail
        as a 500 from Postgres. Rejecting it in the service turns the same
        mistake into a 422 that names the field.
        """
        try:
            valid = NotifyLevel(level)
        except ValueError:
            raise ValueError(f"unknown notify level: {level!r}") from None
        # Read first, so an unknown user raises before anything is written.
        self.get(user_id)
        self._repo.set_notify_level(user_id, valid.value)
        return self.get(user_id)

    def set_name(self, user_id: str, name: str | None) -> Profile:
        # Blank means "no name": trim, cap the length, and collapse an empty
        # result to None so the greeting falls back cleanly instead of showing
        # "Good evening, ".
        cleaned = (name or "").strip()[:_MAX_NAME] or None
        self._repo.set_name(user_id, cleaned)
        return self.get(user_id)
