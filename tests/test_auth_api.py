"""Auth HTTP surface, end to end.

Builds the app the way production does but with the in-memory credentials store
and a fake mailer, then drives the real routes: send a code, register with it,
call an authenticated endpoint with the returned token, and refresh. The point is
that the pieces built and unit-tested in isolation actually compose into a
working sign-in over HTTP, and that the dev-header path still exists for local
work.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from backend.integrations.loops import FakeEmailService
from backend.main import create_app
from backend.repositories.credentials_repository import InMemoryCredentialsRepository
from backend.services.auth_service import DefaultAuthService
from backend.services.passwords import FakePasswordHasher
from backend.services.profile import DefaultProfileService
from backend.tokens import TokenCodec
from tests.fakes import FakeGitHubService


def build():
    codec = TokenCodec(
        secret="test-secret-at-least-thirty-two-bytes-long!!",
        issuer="productivity-app",
        audience="app",
        access_ttl=timedelta(minutes=15),
    )
    mail = FakeEmailService()
    repo = InMemoryCredentialsRepository()
    auth = DefaultAuthService(
        repo=repo,
        passwords=FakePasswordHasher(),
        codec=codec,
        send_email=mail.send_otp,
        refresh_ttl=timedelta(days=30),
        otp_ttl=timedelta(minutes=10),
        resend_cooldown=timedelta(seconds=60),
        max_attempts=5,
    )
    app = create_app(
        github=FakeGitHubService(),
        auth_mode="own",
        token_codec=codec,
        auth_service=auth,
        profile_service=DefaultProfileService(repo=repo),
    )
    return TestClient(app), mail


def test_full_signup_then_authenticated_feed():
    client, mail = build()

    assert client.post("/auth/otp/send", json={"email": "a@example.com"}).status_code == 200
    code = mail.last_code("a@example.com")

    assert (
        client.post(
            "/auth/otp/verify", json={"email": "a@example.com", "code": code}
        ).status_code
        == 200
    )

    registered = client.post(
        "/auth/register",
        json={"email": "a@example.com", "code": code, "password": "hunter2-hunter2"},
    )
    assert registered.status_code == 201
    access = registered.json()["access_token"]

    feed = client.get("/feed", headers={"Authorization": f"Bearer {access}"})
    assert feed.status_code == 200
    assert feed.json() == []


def test_login_after_register_and_refresh_rotates():
    client, mail = build()
    client.post("/auth/otp/send", json={"email": "b@example.com"})
    code = mail.last_code("b@example.com")
    client.post(
        "/auth/register",
        json={"email": "b@example.com", "code": code, "password": "hunter2-hunter2"},
    )

    login = client.post(
        "/auth/login", json={"email": "b@example.com", "password": "hunter2-hunter2"}
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    rotated = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != refresh_token

    # The rotated-away token is now theft if presented again.
    assert client.post("/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401


def test_wrong_password_is_401():
    client, mail = build()
    client.post("/auth/otp/send", json={"email": "c@example.com"})
    code = mail.last_code("c@example.com")
    client.post(
        "/auth/register",
        json={"email": "c@example.com", "code": code, "password": "hunter2-hunter2"},
    )
    bad = client.post(
        "/auth/login", json={"email": "c@example.com", "password": "nope-nope-nope"}
    )
    assert bad.status_code == 401


def test_register_with_wrong_code_is_400():
    client, _ = build()
    client.post("/auth/otp/send", json={"email": "d@example.com"})
    bad = client.post(
        "/auth/register",
        json={"email": "d@example.com", "code": "000000", "password": "hunter2-hunter2"},
    )
    assert bad.status_code == 400


def test_short_password_is_422():
    client, mail = build()
    client.post("/auth/otp/send", json={"email": "e@example.com"})
    code = mail.last_code("e@example.com")
    resp = client.post(
        "/auth/register",
        json={"email": "e@example.com", "code": code, "password": "short"},
    )
    assert resp.status_code == 422


def test_dev_mode_header_still_works():
    app = create_app(github=FakeGitHubService(), auth_mode="dev")
    client = TestClient(app)
    assert client.get("/feed", headers={"X-User-Id": "me"}).status_code == 200


def _register(client, mail, email="p@example.com"):
    client.post("/auth/otp/send", json={"email": email})
    code = mail.last_code(email)
    resp = client.post(
        "/auth/register",
        json={"email": email, "code": code, "password": "hunter2-hunter2"},
    )
    return resp.json()["access_token"]


def test_me_starts_with_no_name_then_patch_sets_it():
    client, mail = build()
    access = _register(client, mail)
    auth = {"Authorization": f"Bearer {access}"}

    me = client.get("/me", headers=auth)
    assert me.status_code == 200
    assert me.json() == {"email": "p@example.com", "name": None}

    patched = client.patch("/me", json={"name": "  Vicky  "}, headers=auth)
    assert patched.status_code == 200
    assert patched.json()["name"] == "Vicky"

    # Durable: a fresh GET reflects it.
    assert client.get("/me", headers=auth).json()["name"] == "Vicky"


def test_me_requires_auth():
    client, _ = build()
    assert client.get("/me").status_code == 401


def test_patch_me_with_blank_clears_the_name():
    client, mail = build()
    access = _register(client, mail, "q@example.com")
    auth = {"Authorization": f"Bearer {access}"}
    client.patch("/me", json={"name": "Vicky"}, headers=auth)
    cleared = client.patch("/me", json={"name": "  "}, headers=auth)
    assert cleared.json()["name"] is None
