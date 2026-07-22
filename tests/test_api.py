from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.feed import UserPreferences
from tests.fakes import FakeGitHubService, make_event

prefs = UserPreferences(user_id="me")


def test_feed_endpoint_returns_ranked_items():
    app = create_app(github=FakeGitHubService())
    svc = app.state.feed_service
    svc.ingest("me", make_event(source_ref="octo/repo#1", reason="subscribed"), prefs)
    svc.ingest(
        "me", make_event(source_ref="octo/repo#2", reason="approval_requested"), prefs
    )

    client = TestClient(app)
    response = client.get("/feed", headers={"X-User-Id": "me"})

    assert response.status_code == 200
    assert [row["action_type"] for row in response.json()] == ["approve", "fyi"]


def test_action_endpoint_comments_and_marks_acted():
    github = FakeGitHubService()
    app = create_app(github=github)
    svc = app.state.feed_service
    item = svc.ingest(
        "me", make_event(source_ref="octo/repo#7", reason="review_requested"), prefs
    )

    client = TestClient(app)
    response = client.post(
        f"/feed/{item.id}/actions", json={"body": "LGTM"}, headers={"X-User-Id": "me"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "acted"
    assert github.comments[0][1] == "LGTM"


def test_action_on_missing_item_returns_404():
    app = create_app(github=FakeGitHubService())
    client = TestClient(app)
    response = client.post(
        "/feed/nope/actions", json={"body": "x"}, headers={"X-User-Id": "me"}
    )
    assert response.status_code == 404


def test_feed_is_isolated_per_user_via_header():
    app = create_app(github=FakeGitHubService())
    svc = app.state.feed_service
    svc.ingest("me", make_event(source_ref="octo/repo#1"), prefs)

    client = TestClient(app)
    assert len(client.get("/feed", headers={"X-User-Id": "me"}).json()) == 1
    assert client.get("/feed", headers={"X-User-Id": "someone-else"}).json() == []
