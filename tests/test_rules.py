"""Rule classifier: the deterministic half of section 3 of the MVP plan.

A wrong tier is the product failing, so this is the fixture suite the plan calls
the highest-value tests in the project. Every row of 3.1 gets a case, and the
precedence ladder of 3.7 gets its own block.
"""

from __future__ import annotations

import pytest

from backend.models.identity import Identity
from backend.models.tiers import Tier, TypeTag
from backend.services.rules import DefaultRuleClassifier
from tests.fakes import make_event

ME = Identity(github_login="vicky")


@pytest.fixture
def rules() -> DefaultRuleClassifier:
    return DefaultRuleClassifier()


# --- 3.1 GitHub rows -------------------------------------------------------


@pytest.mark.parametrize(
    "reason,expected_tier,expected_tag",
    [
        ("review_requested", Tier.URGENT, TypeTag.REVIEW),
        ("approval_requested", Tier.URGENT, TypeTag.APPROVE),
        ("security_alert", Tier.URGENT, TypeTag.ALERT),
        ("invitation", Tier.TODAY, TypeTag.DECIDE),
        ("state_change", Tier.NOISE, TypeTag.FYI),
        ("subscribed", Tier.NOISE, TypeTag.FYI),
    ],
)
def test_deterministic_reasons(rules, reason, expected_tier, expected_tag):
    verdict = rules.classify(make_event(reason=reason), identity=ME)
    assert verdict.tier is expected_tier
    assert verdict.type_tag is expected_tag
    assert verdict.needs_llm is False


def test_ci_failure_on_my_own_pr_is_urgent(rules):
    event = make_event(
        reason="ci_activity", check_conclusion="failure", subject_author="vicky"
    )
    verdict = rules.classify(event, identity=ME)
    assert verdict.tier is Tier.URGENT
    assert verdict.type_tag is TypeTag.ALERT


def test_ci_failure_on_someone_elses_pr_is_not_urgent(rules):
    """The rule is scoped to *your* PR. Someone else's red build is not your
    emergency, and mis-scoping it would flood the urgent tier."""
    event = make_event(
        reason="ci_activity", check_conclusion="failure", subject_author="priya"
    )
    verdict = rules.classify(event, identity=ME)
    assert verdict.tier is Tier.NOISE


def test_ci_success_is_noise(rules):
    event = make_event(
        reason="ci_activity", check_conclusion="success", subject_author="vicky"
    )
    assert rules.classify(event, identity=ME).tier is Tier.NOISE


@pytest.mark.parametrize("reason", ["assign", "mention", "team_mention", "comment"])
def test_ambiguous_reasons_defer_to_the_llm(rules, reason):
    verdict = rules.classify(make_event(reason=reason), identity=ME)
    assert verdict.needs_llm is True


def test_assignment_floor_is_today_never_can_wait(rules):
    """The correction that drove section 3.1: an assigned issue is never filed
    as Can wait by default. Today is the floor the LLM may move from."""
    verdict = rules.classify(
        make_event(reason="assign", subject_type="Issue"), identity=ME
    )
    assert verdict.tier is Tier.TODAY
    assert verdict.type_tag is TypeTag.ASSIGNED


def test_urgent_label_promotes_an_assignment_without_the_llm(rules):
    """Labels are structured data, so no model is needed to read them."""
    verdict = rules.classify(
        make_event(reason="assign", subject_type="Issue", labels=["P0", "backend"]),
        identity=ME,
    )
    assert verdict.tier is Tier.URGENT
    assert verdict.needs_llm is False


def test_unknown_reason_falls_back_to_noise_not_urgent(rules):
    verdict = rules.classify(make_event(reason="something_new"), identity=ME)
    assert verdict.tier is Tier.NOISE
    assert verdict.type_tag is TypeTag.FYI


# --- 3.7 precedence --------------------------------------------------------


def test_security_alert_outranks_a_review_request(rules):
    event = make_event(reason="security_alert", review_requested=True)
    assert rules.classify(event, identity=ME).type_tag is TypeTag.ALERT


def test_ci_failure_outranks_a_review_request(rules):
    """A PR can have your review requested and a failing check at once. The
    card must carry exactly one tag, and 3.7 says the failure wins."""
    event = make_event(
        reason="review_requested",
        check_conclusion="failure",
        subject_author="vicky",
    )
    assert rules.classify(event, identity=ME).type_tag is TypeTag.ALERT


def test_approval_outranks_review(rules):
    event = make_event(reason="review_requested", approval_requested=True)
    assert rules.classify(event, identity=ME).type_tag is TypeTag.APPROVE


def test_changes_requested_on_my_pr_needs_a_decision(rules):
    event = make_event(
        reason="subscribed", review_state="changes_requested", subject_author="vicky"
    )
    verdict = rules.classify(event, identity=ME)
    assert verdict.tier is Tier.TODAY
    assert verdict.type_tag is TypeTag.DECIDE
