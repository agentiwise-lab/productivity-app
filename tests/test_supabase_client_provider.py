"""Contract for the per-thread Supabase client provider.

The `/feed` 500s (`httpx.ReadError: [Errno 11] Resource temporarily
unavailable`) came from one supabase-py client — whose httpx transports are not
safe to share across the request threadpool plus the classify/webhook pools —
being used concurrently. The provider's contract: one client per thread, built
lazily, reused within a thread.
"""

from __future__ import annotations

import threading

from backend.repositories.supabase_client import SupabaseClientProvider


def test_same_thread_reuses_one_client() -> None:
    calls = {"n": 0}

    def factory() -> object:
        calls["n"] += 1
        return object()

    provider = SupabaseClientProvider(factory)
    first = provider.get()
    second = provider.get()

    assert first is second
    assert calls["n"] == 1


def test_each_thread_gets_its_own_client() -> None:
    counter = {"n": 0}
    counter_lock = threading.Lock()

    def factory() -> str:
        with counter_lock:
            counter["n"] += 1
            return f"client-{counter['n']}"

    provider = SupabaseClientProvider(factory)
    n = 8
    barrier = threading.Barrier(n)  # keep every thread alive at once
    seen: list[str] = []
    seen_lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        client = provider.get()
        assert provider.get() is client  # reused within the thread
        with seen_lock:
            seen.append(client)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Each concurrent thread built exactly one distinct client.
    assert len(seen) == n
    assert len(set(seen)) == n
