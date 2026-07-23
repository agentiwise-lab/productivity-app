from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.feed import UserPreferences
from tests.fakes import FakeGitHubService, make_event

prefs = UserPreferences(user_id="me")

USER = "8f1c2c1e-0000-4000-8000-000000000001"

NOTIFICATION = {
    "id": "1",
    "reason": "review_requested",
    "repository": {"full_name": "octo/repo"},
    "subject": {
        "type": "PullRequest",
        "title": "Add rate limiting",
        "url": "https://api.github.com/repos/octo/repo/pulls/42",
    },
    "updated_at": "2026-07-23T11:00:00Z",
}


def dev_app(**kwargs):
    return create_app(github=FakeGitHubService(), auth_mode="dev", **kwargs)


def test_feed_endpoint_returns_ranked_items():
    app = dev_app()
    svc = app.state.feed_service
    svc.ingest("me", make_event(source_ref="octo/repo#1", reason="subscribed"), prefs)
    svc.ingest(
        "me", make_event(source_ref="octo/repo#2", reason="approval_requested"), prefs
    )

    client = TestClient(app)
    response = client.get("/feed", headers={"X-User-Id": "me"})

    assert response.status_code == 200
    body = response.json()
    assert [row["type_tag"] for row in body] == ["approve", "fyi"]
    # The tier and the score exist only on the wire, never in a stored column.
    assert [row["tier"] for row in body] == ["urgent", "noise"]
    assert body[0]["priority_score"] > body[1]["priority_score"]


def test_action_endpoint_comments_and_marks_acted():
    github = FakeGitHubService()
    app = create_app(github=github, auth_mode="dev")
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
    client = TestClient(dev_app())
    response = client.post(
        "/feed/nope/actions", json={"body": "x"}, headers={"X-User-Id": "me"}
    )
    assert response.status_code == 404


def test_feed_is_isolated_per_user():
    app = dev_app()
    app.state.feed_service.ingest("me", make_event(source_ref="octo/repo#1"), prefs)

    client = TestClient(app)
    assert len(client.get("/feed", headers={"X-User-Id": "me"}).json()) == 1
    assert client.get("/feed", headers={"X-User-Id": "someone-else"}).json() == []


# --- auth ------------------------------------------------------------------


def test_the_dev_header_is_refused_outside_dev_mode():
    """A trusted user-id header is the exact thing plan 6.5 forbids. It exists
    for local development, so it must be impossible to leave on by accident."""
    app = create_app(github=FakeGitHubService(), auth_mode="supabase", jwt_secret="s")
    client = TestClient(app)
    assert client.get("/feed", headers={"X-User-Id": "me"}).status_code == 401


def test_supabase_mode_requires_a_valid_token():
    app = create_app(github=FakeGitHubService(), auth_mode="supabase", jwt_secret="s")
    client = TestClient(app)
    assert client.get("/feed").status_code == 401
    assert (
        client.get("/feed", headers={"Authorization": "Bearer nonsense"}).status_code
        == 401
    )


def test_supabase_mode_reads_the_user_from_the_verified_token():
    import jwt

    app = create_app(
        github=FakeGitHubService(), auth_mode="supabase", jwt_secret="topsecret"
    )
    token = jwt.encode({"sub": USER, "aud": "authenticated"}, "topsecret", "HS256")
    client = TestClient(app)
    response = client.get("/feed", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == []


def test_a_token_signed_with_the_wrong_key_is_refused():
    import jwt

    app = create_app(
        github=FakeGitHubService(), auth_mode="supabase", jwt_secret="topsecret"
    )
    forged = jwt.encode({"sub": USER, "aud": "authenticated"}, "guess", "HS256")
    client = TestClient(app)
    assert (
        client.get("/feed", headers={"Authorization": f"Bearer {forged}"}).status_code
        == 401
    )


# --- webhook ---------------------------------------------------------------


def envelope(user_id=USER):
    return {
        "id": "msg_1",
        "type": "composio.trigger.message",
        "timestamp": "2026-07-23T12:00:00Z",
        "data": NOTIFICATION,
        "metadata": {
            "user_id": user_id,
            "trigger_slug": "GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER",
            "connected_account_id": "ca_1",
        },
    }


def test_a_verified_webhook_creates_a_feed_item():
    app = create_app(
        github=FakeGitHubService(),
        auth_mode="dev",
        verify_webhook=lambda body, headers: envelope(),
    )
    client = TestClient(app)
    response = client.post("/webhooks/composio", json=envelope())

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert len(app.state.feed_service.list_feed(USER)) == 1


def test_an_unverified_webhook_is_refused_and_writes_nothing():
    def reject(body, headers):
        raise ValueError("bad signature")

    app = create_app(
        github=FakeGitHubService(), auth_mode="dev", verify_webhook=reject
    )
    client = TestClient(app)
    response = client.post("/webhooks/composio", json=envelope())

    assert response.status_code == 401
    assert app.state.feed_service.list_feed(USER) == []


def test_an_unmapped_trigger_returns_200_so_it_is_not_redelivered_forever():
    """Composio retries a failed webhook. Returning an error for something we
    have simply chosen not to handle would turn that into an endless loop."""
    unmapped = envelope()
    unmapped["metadata"]["trigger_slug"] = "SOMETHING_ELSE"
    app = create_app(
        github=FakeGitHubService(),
        auth_mode="dev",
        verify_webhook=lambda body, headers: unmapped,
    )
    response = TestClient(app).post("/webhooks/composio", json=unmapped)

    assert response.status_code == 200
    assert response.json()["handled"] is False


# --- acting ----------------------------------------------------------------


def test_snooze_endpoint_hides_the_item_until_its_time():
    app = dev_app()
    item = app.state.feed_service.ingest(
        "me", make_event(source_ref="octo/repo#7"), prefs
    )
    client = TestClient(app)

    response = client.post(
        f"/feed/{item.id}/snooze",
        json={"until": "2030-01-01T00:00:00Z"},
        headers={"X-User-Id": "me"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "snoozed"
    # Snoozed is not dismissed: Later still has to show it.
    assert len(client.get("/feed", headers={"X-User-Id": "me"}).json()) == 1


def test_dismiss_endpoint_removes_the_item_from_the_feed():
    app = dev_app()
    item = app.state.feed_service.ingest(
        "me", make_event(source_ref="octo/repo#7"), prefs
    )
    client = TestClient(app)

    response = client.post(f"/feed/{item.id}/dismiss", headers={"X-User-Id": "me"})

    assert response.status_code == 200
    assert client.get("/feed", headers={"X-User-Id": "me"}).json() == []


def test_acting_twice_returns_409_rather_than_sending_again():
    """The app retries on a flaky network. The second attempt must be refused
    by the server, not turned into a second comment on somebody's PR."""
    github = FakeGitHubService()
    app = create_app(github=github, auth_mode="dev")
    item = app.state.feed_service.ingest(
        "me", make_event(source_ref="octo/repo#7"), prefs
    )
    client = TestClient(app)

    first = client.post(
        f"/feed/{item.id}/actions",
        json={"action": "comment", "body": "LGTM"},
        headers={"X-User-Id": "me"},
    )
    second = client.post(
        f"/feed/{item.id}/actions",
        json={"action": "comment", "body": "LGTM"},
        headers={"X-User-Id": "me"},
    )

    assert (first.status_code, second.status_code) == (200, 409)
    assert len(github.comments) == 1


def test_an_unknown_action_is_a_400_not_a_silent_success():
    app = dev_app()
    item = app.state.feed_service.ingest(
        "me", make_event(source_ref="octo/repo#7"), prefs
    )
    response = TestClient(app).post(
        f"/feed/{item.id}/actions",
        json={"action": "teleport", "body": ""},
        headers={"X-User-Id": "me"},
    )
    assert response.status_code == 400


def test_acting_on_another_users_item_is_a_404():
    app = dev_app()
    item = app.state.feed_service.ingest(
        "me", make_event(source_ref="octo/repo#7"), prefs
    )
    response = TestClient(app).post(
        f"/feed/{item.id}/actions",
        json={"action": "comment", "body": "hi"},
        headers={"X-User-Id": "intruder"},
    )
    assert response.status_code == 404


# --- fetch on open ---------------------------------------------------------


def test_refresh_pulls_notifications_into_the_feed():
    """GitHub's urgent items arrive on open rather than by push, so this is the
    primary GitHub path, not a fallback (plan 10.5)."""
    github = FakeGitHubService(
        notifications=[make_event(source_ref="octo/repo#3", reason="review_requested")]
    )
    app = create_app(github=github, auth_mode="dev")
    client = TestClient(app)

    response = client.post("/feed/refresh", headers={"X-User-Id": "me"})

    assert response.status_code == 200
    assert response.json()["ingested"] == 1
    assert [row["tier"] for row in client.get("/feed", headers={"X-User-Id": "me"}).json()] == [
        "urgent"
    ]


def test_refresh_is_idempotent():
    github = FakeGitHubService(
        notifications=[make_event(source_ref="octo/repo#3", reason="review_requested")]
    )
    app = create_app(github=github, auth_mode="dev")
    client = TestClient(app)
    client.post("/feed/refresh", headers={"X-User-Id": "me"})
    client.post("/feed/refresh", headers={"X-User-Id": "me"})

    assert len(client.get("/feed", headers={"X-User-Id": "me"}).json()) == 1
