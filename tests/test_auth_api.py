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
from backend.repositories.device_token_repository import InMemoryDeviceTokenRepository
from backend.services.auth_service import DefaultAuthService
from backend.services.passwords import FakePasswordHasher
from backend.services.profile import DefaultProfileService
from backend.tokens import TokenCodec
from tests.fakes import FakeGitHubService


def build(with_devices: bool = False):
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
    devices = InMemoryDeviceTokenRepository()
    app = create_app(
        github=FakeGitHubService(),
        auth_mode="own",
        token_codec=codec,
        auth_service=auth,
        profile_service=DefaultProfileService(repo=repo),
        device_tokens=devices,
    )
    client = TestClient(app)
    return (client, mail, devices) if with_devices else (client, mail)


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
    # The whole payload, deliberately: /me is what the app renders the You tab
    # from, so a field appearing or vanishing should fail here rather than be
    # discovered on a phone.
    assert me.json() == {
        "email": "p@example.com",
        "name": None,
        "notify_level": "urgent",
    }

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


# --- notification settings and devices -------------------------------------


def test_patch_me_sets_the_notify_level():
    client, mail = build()
    access = _register(client, mail, "n1@example.com")
    auth = {"Authorization": f"Bearer {access}"}

    assert client.get("/me", headers=auth).json()["notify_level"] == "urgent"

    patched = client.patch("/me", json={"notify_level": "all"}, headers=auth)
    assert patched.status_code == 200
    assert patched.json()["notify_level"] == "all"
    assert client.get("/me", headers=auth).json()["notify_level"] == "all"


def test_patching_only_the_name_leaves_the_notify_level_alone():
    """`None` means "clear" for the name and "unchanged" for the level. The
    asymmetry is deliberate and this is what pins it: a name edit from the You
    tab must not silently reset somebody's notification setting."""
    client, mail = build()
    access = _register(client, mail, "n2@example.com")
    auth = {"Authorization": f"Bearer {access}"}

    client.patch("/me", json={"notify_level": "off"}, headers=auth)
    client.patch("/me", json={"name": "Vicky"}, headers=auth)

    me = client.get("/me", headers=auth).json()
    assert me == {"email": "n2@example.com", "name": "Vicky", "notify_level": "off"}


def test_patching_only_the_level_leaves_the_name_alone():
    client, mail = build()
    access = _register(client, mail, "n3@example.com")
    auth = {"Authorization": f"Bearer {access}"}

    client.patch("/me", json={"name": "Vicky"}, headers=auth)
    client.patch("/me", json={"notify_level": "urgent_today"}, headers=auth)

    me = client.get("/me", headers=auth).json()
    assert me["name"] == "Vicky"
    assert me["notify_level"] == "urgent_today"


def test_an_unknown_notify_level_is_422_not_500():
    client, mail = build()
    access = _register(client, mail, "n4@example.com")
    resp = client.patch(
        "/me",
        json={"notify_level": "sometimes"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 422


def test_registering_a_device_then_unregistering_it():
    client, mail, devices = build(with_devices=True)
    access = _register(client, mail, "d1@example.com")
    auth = {"Authorization": f"Bearer {access}"}
    token = "ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]"

    assert client.post(
        "/devices", json={"token": token, "platform": "android"}, headers=auth
    ).status_code == 204

    user_id = client.get("/me", headers=auth) and _subject(access)
    assert devices.tokens_for(user_id) == [token]

    assert client.post(
        "/devices/unregister", json={"token": token}, headers=auth
    ).status_code == 204
    assert devices.tokens_for(user_id) == []


def test_registering_the_same_device_twice_is_idempotent():
    """The app re-registers on every launch, because a token can rotate."""
    client, mail, devices = build(with_devices=True)
    access = _register(client, mail, "d2@example.com")
    auth = {"Authorization": f"Bearer {access}"}
    token = "ExponentPushToken[bbbbbbbbbbbbbbbbbbbbbb]"

    for _ in range(3):
        client.post(
            "/devices", json={"token": token, "platform": "ios"}, headers=auth
        )

    assert devices.tokens_for(_subject(access)) == [token]


def test_a_device_registered_by_a_second_user_moves_to_them():
    """Sign out on a phone, sign in as somebody else. If the row kept the first
    user, their work would keep arriving on the new owner's lock screen."""
    client, mail, devices = build(with_devices=True)
    first = _register(client, mail, "d3@example.com")
    second = _register(client, mail, "d4@example.com")
    token = "ExponentPushToken[cccccccccccccccccccccc]"

    client.post(
        "/devices",
        json={"token": token, "platform": "android"},
        headers={"Authorization": f"Bearer {first}"},
    )
    client.post(
        "/devices",
        json={"token": token, "platform": "android"},
        headers={"Authorization": f"Bearer {second}"},
    )

    assert devices.tokens_for(_subject(first)) == []
    assert devices.tokens_for(_subject(second)) == [token]


def test_unregistering_a_token_that_was_never_registered_is_not_an_error():
    client, mail = build()
    access = _register(client, mail, "d5@example.com")
    resp = client.post(
        "/devices/unregister",
        json={"token": "ExponentPushToken[nope]"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 204


def test_an_unknown_platform_is_rejected():
    """The column has a check constraint, so an unknown value would be a 500
    from Postgres rather than a 422 naming the field."""
    client, mail = build()
    access = _register(client, mail, "d6@example.com")
    resp = client.post(
        "/devices",
        json={"token": "ExponentPushToken[x]", "platform": "blackberry"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 422


def test_the_device_routes_require_auth():
    """A push token is a send-anything-to-this-device capability. An
    unauthenticated write would let anyone point a stranger's device at an
    account."""
    client, _ = build()
    assert client.post(
        "/devices", json={"token": "t", "platform": "ios"}
    ).status_code == 401
    assert client.post("/devices/unregister", json={"token": "t"}).status_code == 401


def _subject(access_token: str) -> str:
    """The user id the token was minted for, read without verifying: these are
    tests, and the id is all that is wanted."""
    import base64
    import json

    payload = access_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))["sub"]
