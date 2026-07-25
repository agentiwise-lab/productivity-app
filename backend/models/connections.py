"""A stored connection: which of a user's provider accounts is linked, and the
identity we resolved for it.

This is the ``public.connections`` row as the code sees it. It holds no tokens:
Composio owns those. What we keep is the pointer to Composio's account
(``composio_connected_account_id``), the key we linked it under
(``composio_user_id``, which is the app user's uuid), its health, and the
provider-side identity ("is this my PR" needs the GitHub login; Slack mention
detection needs the user id).
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.models.identity import Identity


class ConnectionRow(BaseModel):
    user_id: str
    provider: str
    composio_user_id: str
    composio_connected_account_id: str | None = None
    # The DB connection_status vocabulary: active | expired | revoked | error |
    # initiated. Kept as a string rather than an app enum because this is the
    # storage shape, and the app-facing ConnectionStatus is a separate mapping.
    status: str = "active"
    provider_login: str | None = None
    provider_user_id: str | None = None

    def identity(self) -> Identity:
        """The provider-side identity, shaped for whoever asks. Only the fields
        a provider actually has are populated; the Slack self-DM channel is not
        stored here and resolves to None."""
        if self.provider == "github":
            return Identity(github_login=self.provider_login)
        if self.provider == "slack":
            return Identity(slack_user_id=self.provider_user_id)
        return Identity()
