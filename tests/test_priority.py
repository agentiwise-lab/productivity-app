from datetime import datetime, timedelta, timezone

from backend.models.feed import ActionType, FeedItem, UserPreferences
from backend.services.priority import DefaultPriorityService

svc = DefaultPriorityService()
prefs = UserPreferences(user_id="me")


def item(**overrides) -> FeedItem:
    defaults = dict(
        id="1",
        user_id="me",
        source_ref="octo/repo#1",
        action_type=ActionType.REVIEW,
        title="t",
        url="u",
        repo="octo/repo",
    )
    defaults.update(overrides)
    return FeedItem(**defaults)


def test_action_weight_orders_approve_over_fyi():
    approve = svc.score(item(action_type=ActionType.APPROVE), prefs)
    fyi = svc.score(item(action_type=ActionType.FYI), prefs)
    assert approve > fyi


def test_blocking_boosts_score():
    assert svc.score(item(is_blocking=True), prefs) > svc.score(
        item(is_blocking=False), prefs
    )


def test_muted_repo_zeroes_score():
    muted = UserPreferences(user_id="me", muted_repos={"octo/repo"})
    assert svc.score(item(), muted) == 0.0


def test_priority_repo_boost():
    boosted = UserPreferences(user_id="me", priority_repos={"octo/repo"})
    assert svc.score(item(), boosted) > svc.score(item(), prefs)


def test_vip_actor_boost():
    from backend.models.feed import Actor

    vip = UserPreferences(user_id="me", vip_actors={"boss"})
    with_vip = item(actors=[Actor(login="boss")])
    assert svc.score(with_vip, vip) > svc.score(with_vip, prefs)


def test_overdue_deadline_outranks_far_deadline():
    overdue = item(deadline=datetime.now(timezone.utc) - timedelta(hours=1))
    far = item(deadline=datetime.now(timezone.utc) + timedelta(days=10))
    assert svc.score(overdue, prefs) > svc.score(far, prefs)
