import pytest

from backend.models.feed import ActionType
from backend.services.classification import DefaultClassificationService
from tests.fakes import make_event

svc = DefaultClassificationService()


@pytest.mark.parametrize(
    "reason,expected",
    [
        ("review_requested", ActionType.REVIEW),
        ("approval_requested", ActionType.APPROVE),
        ("mention", ActionType.REPLY),
        ("team_mention", ActionType.REPLY),
        ("comment", ActionType.REPLY),
        ("assign", ActionType.DECIDE),
        ("security_alert", ActionType.DECIDE),
        ("state_change", ActionType.FYI),
        ("subscribed", ActionType.FYI),
        ("something_new_github_added", ActionType.FYI),  # unknown -> FYI
    ],
)
def test_classify_by_reason(reason, expected):
    assert svc.classify(make_event(reason=reason)) == expected


def test_changes_requested_overrides_to_decide():
    event = make_event(reason="review_requested", review_state="changes_requested")
    assert svc.classify(event) == ActionType.DECIDE


def test_ci_failure_is_decide_but_success_is_fyi():
    assert (
        svc.classify(make_event(reason="ci_activity", check_conclusion="failure"))
        == ActionType.DECIDE
    )
    assert (
        svc.classify(make_event(reason="ci_activity", check_conclusion="success"))
        == ActionType.FYI
    )
