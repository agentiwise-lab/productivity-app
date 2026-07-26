"""One Supabase client per thread.

supabase-py's sync ``Client`` wraps httpx transports that are not safe to share
across the request threadpool plus the classify/webhook pools. Under concurrency
a shared client surfaces ``httpx.ReadError: [Errno 11] Resource temporarily
unavailable`` and the request 500s (the ``/feed`` failures). Giving each thread
its own lazily-built client removes the shared mutable transport. Worker threads
are long-lived and few, so the number of clients stays small and bounded.

The repositories take a provider and expose ``_db`` as a property returning
``provider.get()``, so their query code is unchanged.
"""

from __future__ import annotations

import threading
from typing import Any, Callable


class SupabaseClientProvider:
    def __init__(self, factory: Callable[[], Any]) -> None:
        self._factory = factory
        self._local = threading.local()

    def get(self) -> Any:
        client = getattr(self._local, "client", None)
        if client is None:
            client = self._factory()
            self._local.client = client
        return client
