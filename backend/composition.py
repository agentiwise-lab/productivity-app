"""Composition root: the only place that reads configuration.

Everything else takes its dependencies as arguments. Keeping ``os.environ`` out
of the services is what lets the whole backend be tested without a single
credential, and it means a misconfiguration surfaces here, at start-up, rather
than at the first webhook.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import FastAPI

from backend.integrations.factory import ComposioIntegrations
from backend.integrations.openrouter import DefaultTriageModel
from backend.integrations.loops import LoopsEmailService
from backend.main import create_app
from backend.models.sources import Source
from backend.repositories.connections import InMemoryConnectionRepository
from backend.repositories.credentials_repository import (
    CredentialsRepository,
    InMemoryCredentialsRepository,
)
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.auth_service import DefaultAuthService
from backend.services.connections import DefaultConnectionService
from backend.services.later import LaterService
from backend.services.passwords import Argon2PasswordHasher
from backend.services.stats import SourceStatsService
from backend.services.sync import SourceSync
from backend.services.triggers import DefaultTriggerProvisioner
from backend.services.feed import DefaultFeedService
from backend.services.rules import DefaultRuleClassifier
from backend.services.classifier import (
    DefaultClassificationService,
    InMemoryClassificationCache,
)
from backend.tokens import TokenCodec

log = logging.getLogger(__name__)


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def build_app() -> FastAPI:
    load_dotenv()

    from composio import Composio

    composio = Composio(api_key=_require("COMPOSIO_API_KEY"))
    # A dev-only fallback id for the in-memory connection store's live identity
    # resolution. Production uses the Supabase store and the per-user id, and
    # never this. It is optional precisely so it cannot become a shared account.
    composio_user = os.environ.get("COMPOSIO_USER_ID")

    # The persisted connection store: written by the connect flow (mark_active)
    # and read by ingest (identity_for). Supabase in production, in-memory (with
    # a live-resolution fallback) for local work.
    connections = _build_connection_repository(composio, composio_user)

    repo = _build_repository()
    classifier = DefaultClassificationService(
        model=DefaultTriageModel(),
        repo=repo,
        cache=InMemoryClassificationCache(),
        daily_budget=int(os.environ.get("LLM_DAILY_BUDGET", "200")),
        model_name=os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
    )

    connection_service = DefaultConnectionService(
        composio,
        auth_config_ids=_auth_config_ids(),
        repo=connections,
        provisioner=DefaultTriggerProvisioner(composio),
        callback_url=os.environ.get("COMPOSIO_CALLBACK_URL", ""),
    )
    # One factory mints each user's own bound integration services on demand, so
    # every read and write acts against the caller's account, not a shared one.
    integrations = ComposioIntegrations(composio)

    # The sync needs a feed service of its own, built on the same repository
    # and rules the API uses, so both paths write identical rows.
    sync = SourceSync(
        feed=DefaultFeedService(
            repo=repo, rules=DefaultRuleClassifier(), integrations=integrations
        ),
        integrations=integrations,
        classifier=classifier,
        identity_for=connections.identity_for,
        classify_async=True,
    )

    stats = SourceStatsService(
        integrations=integrations, identity_for=connections.identity_for
    )

    # Later reads the providers directly and stores nothing, so it takes the
    # integrations factory rather than the repository.
    later = LaterService(
        integrations=integrations, identity_for=connections.identity_for
    )

    webhook_secret = os.environ.get("COMPOSIO_WEBHOOK_SECRET")

    def verify_webhook(body: bytes, headers: dict) -> dict:
        """Raises on a bad signature, which the route turns into a 401.

        The secret is required. A missing one would otherwise mean accepting any
        POST to a public URL as a genuine event for any user id it names.
        """
        if not webhook_secret:
            raise RuntimeError("COMPOSIO_WEBHOOK_SECRET is not set")
        result = composio.triggers.parse(
            body=body, headers=headers, verify_secret=webhook_secret
        )
        return result["raw_payload"]

    auth_mode = os.environ.get("AUTH_MODE", "own")
    if auth_mode == "dev":
        log.warning(
            "AUTH_MODE=dev: the X-User-Id header is trusted. Local use only."
        )

    codec = TokenCodec(
        secret=_require("AUTH_JWT_SECRET") if auth_mode == "own" else "dev",
        issuer=os.environ.get("AUTH_JWT_ISSUER", "productivity-app"),
        audience=os.environ.get("AUTH_JWT_AUDIENCE", "app"),
        access_ttl=timedelta(minutes=int(os.environ.get("AUTH_ACCESS_TTL_MIN", "15"))),
    )
    email_service = LoopsEmailService(
        api_key=os.environ.get("LOOPS_API_KEY"),
        otp_transactional_id=os.environ.get("LOOPS_OTP_TRANSACTIONAL_ID"),
    )
    auth_service = DefaultAuthService(
        repo=_build_credentials_repository(),
        passwords=Argon2PasswordHasher(),
        codec=codec,
        send_email=email_service.send_otp,
        refresh_ttl=timedelta(days=int(os.environ.get("AUTH_REFRESH_TTL_DAYS", "30"))),
        otp_ttl=timedelta(minutes=int(os.environ.get("OTP_TTL_MIN", "10"))),
        resend_cooldown=timedelta(
            seconds=int(os.environ.get("OTP_RESEND_COOLDOWN_SEC", "60"))
        ),
        max_attempts=int(os.environ.get("OTP_MAX_ATTEMPTS", "5")),
    )

    return create_app(
        repo=repo,
        integrations=integrations,
        connections=connections,
        auth_mode=auth_mode,
        token_codec=codec,
        auth_service=auth_service,
        classifier=classifier,
        connection_service=connection_service,
        stats=stats,
        later=later,
        sync=sync,
        verify_webhook=verify_webhook,
        cors_origins=[
            origin.strip()
            for origin in os.environ.get("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ],
    )


def _build_repository():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log.warning("Supabase is not configured; using the in-memory store")
        return InMemoryFeedRepository()

    from supabase import create_client

    from backend.repositories.supabase_feed_repository import SupabaseFeedRepository

    return SupabaseFeedRepository(create_client(url, key))


#: Which env var holds each toolkit's Composio auth config id (ac_...). These are
#: created once in the Composio dashboard; a source with no id cannot be
#: connected and the link route answers 503 for it.
_AUTH_CONFIG_ENV: dict[Source, str] = {
    Source.GITHUB: "COMPOSIO_AUTH_CONFIG_GITHUB",
    Source.SLACK: "COMPOSIO_AUTH_CONFIG_SLACK",
    Source.CALENDAR: "COMPOSIO_AUTH_CONFIG_GOOGLECALENDAR",
    Source.LINEAR: "COMPOSIO_AUTH_CONFIG_LINEAR",
    Source.GMAIL: "COMPOSIO_AUTH_CONFIG_GMAIL",
    Source.GOOGLE_DOCS: "COMPOSIO_AUTH_CONFIG_GOOGLEDOCS",
}


def _auth_config_ids() -> dict[Source, str]:
    return {
        source: os.environ[var]
        for source, var in _AUTH_CONFIG_ENV.items()
        if os.environ.get(var)
    }


def _build_connection_repository(composio, composio_user):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log.warning("Supabase is not configured; connections use the in-memory store")
        return InMemoryConnectionRepository(
            composio=composio, composio_user_id=composio_user
        )

    from supabase import create_client

    from backend.repositories.supabase_connections_repository import (
        SupabaseConnectionRepository,
    )

    return SupabaseConnectionRepository(create_client(url, key))


def _build_credentials_repository() -> CredentialsRepository:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log.warning("Supabase is not configured; auth uses the in-memory store")
        return InMemoryCredentialsRepository()

    from supabase import create_client

    from backend.repositories.supabase_credentials_repository import (
        SupabaseCredentialsRepository,
    )

    return SupabaseCredentialsRepository(create_client(url, key))


app = build_app() if os.environ.get("APP_EAGER_START") else None
