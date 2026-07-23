"""Composition root: the only place that reads configuration.

Everything else takes its dependencies as arguments. Keeping ``os.environ`` out
of the services is what lets the whole backend be tested without a single
credential, and it means a misconfiguration surfaces here, at start-up, rather
than at the first webhook.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from backend.integrations.composio_github import ComposioGitHubService
from backend.integrations.openrouter import DefaultTriageModel
from backend.main import create_app
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.classifier import (
    DefaultClassificationService,
    InMemoryClassificationCache,
)

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
    github = ComposioGitHubService(composio, user_id=_require("COMPOSIO_USER_ID"))

    repo = _build_repository()
    classifier = DefaultClassificationService(
        model=DefaultTriageModel(),
        repo=repo,
        cache=InMemoryClassificationCache(),
        daily_budget=int(os.environ.get("LLM_DAILY_BUDGET", "200")),
        model_name=os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash"),
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

    auth_mode = os.environ.get("AUTH_MODE", "supabase")
    if auth_mode == "dev":
        log.warning(
            "AUTH_MODE=dev: the X-User-Id header is trusted. Local use only."
        )

    return create_app(
        github=github,
        repo=repo,
        auth_mode=auth_mode,
        jwt_secret=os.environ.get("SUPABASE_JWT_SECRET"),
        classifier=classifier,
        verify_webhook=verify_webhook,
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


app = build_app() if os.environ.get("APP_EAGER_START") else None
