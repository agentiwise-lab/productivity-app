"""Who the user is on each connected platform.

Section 3.10 of the plan: several rules cannot be evaluated without this. "Is
this my PR" needs the GitHub login; Slack mention detection needs the user id,
because Slack has no mention trigger and we match ``<@U...>`` in message text
ourselves. Resolved once at connection time and cached on ``connections``.
"""

from __future__ import annotations

from pydantic import BaseModel


class Identity(BaseModel):
    github_login: str | None = None
    slack_user_id: str | None = None
    # The user's conversation with themselves. A note-to-self and a reply you
    # sent in someone else's DM look identical by sender, so this channel id is
    # the only thing that separates "saved for later" from "your own outbound
    # message", which must never come back as something needing you.
    slack_dm_channel: str | None = None

    def is_me_on_github(self, login: str | None) -> bool:
        if login is None or self.github_login is None:
            return False
        return login.lower() == self.github_login.lower()
