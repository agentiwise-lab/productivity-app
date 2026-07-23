"""The fixture suite section 9 of the plan calls the highest-value tests here.

These run a real GitHub notification payload, captured live, all the way from
the wire shape through mapping into rule classification. The unit tests above
cover mapping and rules separately; this covers the seam between them, which is
where a field rename would otherwise pass every test and still break the feed.
"""

from __future__ import annotations

import pytest

from backend.integrations.composio_github import notification_to_raw_event
from backend.models.identity import Identity
from backend.models.tiers import Tier, TypeTag
from backend.services.rules import DefaultRuleClassifier

ME = Identity(github_login="vicky81125")

# The exact shape GITHUB_LIST_NOTIFICATIONS returns, from a live call.
NOTIFICATION = {
    "id": "24512080855",
    "reason": "author",
    "unread": True,
    "updated_at": "2026-07-07T12:31:50Z",
    "repository": {"full_name": "dswh/glued_landing"},
    "subject": {
        "title": "Feature/gif showcase",
        "type": "PullRequest",
        "url": "https://api.github.com/repos/dswh/glued_landing/pulls/23",
        "latest_comment_url": (
            "https://api.github.com/repos/dswh/glued_landing/issues/comments/4903814569"
        ),
    },
}


def classify(**overrides):
    event = notification_to_raw_event({**NOTIFICATION, **overrides})
    return DefaultRuleClassifier().classify(event, identity=ME)


@pytest.mark.parametrize(
    "reason,tier,tag",
    [
        ("review_requested", Tier.URGENT, TypeTag.REVIEW),
        ("approval_requested", Tier.URGENT, TypeTag.APPROVE),
        ("security_alert", Tier.URGENT, TypeTag.ALERT),
        ("invitation", Tier.TODAY, TypeTag.DECIDE),
        ("state_change", Tier.NOISE, TypeTag.FYI),
        ("subscribed", Tier.NOISE, TypeTag.FYI),
        ("author", Tier.NOISE, TypeTag.FYI),
    ],
)
def test_a_real_notification_reaches_the_expected_tier(reason, tier, tag):
    verdict = classify(reason=reason)
    assert (verdict.tier, verdict.type_tag) == (tier, tag)


@pytest.mark.parametrize("reason", ["mention", "comment", "assign"])
def test_prose_reasons_are_handed_to_the_model(reason):
    assert classify(reason=reason).needs_llm is True


def test_your_own_pull_requests_are_noise():
    """Nineteen of nineteen live notifications had reason `author`, because
    opening a PR subscribes you to it. If those were not filtered, the feed
    would open full of the user's own work and nothing else."""
    assert classify(reason="author").tier is Tier.NOISE


def test_the_url_is_clickable_not_an_api_endpoint():
    event = notification_to_raw_event(NOTIFICATION)
    assert event.url == "https://github.com/dswh/glued_landing/pull/23"
    assert "api.github.com" not in event.url
