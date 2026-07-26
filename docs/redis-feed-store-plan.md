# Phase 0 — Redis feed store (storage re-architecture)

Date: 2026-07-26. Precedes the UX work in [realtime-feed-and-ux-plan.md](realtime-feed-and-ux-plan.md). Grounded in the current tree and live session logs.

**Status: DRAFT — for review + approval.**

## Principle (locked with Vicky)

The user's dynamic data is not durably stored. The Home feed (content + LLM classification) lives in **Redis with a 24h TTL**, reset on every append. The only durable store holds what genuinely cannot be re-derived. Later is already live and unchanged (`later.py`: no model, no storage, a live mirror of the provider).

- **Redis (ephemeral):** `feed:{user_id}` = the user's Home feed rows (content + `llm_tier`/`summary`/`reason` + timing + `signal`/`needs_llm`/`llm_attempted_at`). 24h TTL, reset on append. `volatile-lru` eviction under a `maxmemory` cap so it never OOMs (the out-of-memory Vicky hit).
- **Durable Postgres (small, portable to RDS):** `users`, `credentials`, `connections`, `user_preferences`, and a new **action ledger** `feed_actions` (snooze / dismiss / handled, keyed by `(user_id, source_ref)`). This is the entire durable surface, which keeps a future Supabase→AWS move trivial.

## Why classification rides with the feed in Redis (not a separate durable store)

Classification is content-derived and keyed by content-hash. Splitting it into a durable store next to an ephemeral Redis feed forces two systems to agree on TTL and content-version for the sole benefit of avoiding an occasional re-classify after a rare Redis restart (Gemini Flash, cheap). So it rides in the Redis row. On cold Redis: re-pull + re-classify. Optional small `cls:{content_hash}` → verdict map in Redis (24h TTL) to avoid re-classifying identical content across items/users; start without it, add if the classify cost shows.

---

## Data model

**Redis** (`redis-py`, sync client, one connection pool):
- `feed:{user_id}` — a **hash**: field = `source_ref`, value = JSON of the assembled row (the `FeedItem` shape minus the user-state columns, which live in the ledger). `EXPIRE feed:{user_id} 86400` on every write.
- Optional `cls:{content_hash}` — string JSON `(tier, summary, reason)`, `EX 86400`.

Per-user footprint is small: the Home feed is tens of rows (this account: 16–37), not the Later firehose. Whole-user eviction is the unit, which matches "evict a user's entries first when memory fills."

**Postgres** — new table (migration 0010):
```
feed_actions (
  user_id uuid, source_ref text,
  status text,            -- unread | acted | dismissed | snoozed
  snoozed_until timestamptz, handled_at timestamptz,
  updated_at timestamptz,
  primary key (user_id, source_ref)
)
```
The ledger is the source of truth for user state. `feed_items` is dropped (migration 0010 also drops it; near-zero data in dev).

---

## Flows

- **Read (`GET /feed`)** — cache-only, fast: `HGETALL feed:{uid}` → deserialize rows → **overlay the ledger** (drop `dismissed`, hide `snoozed_until > now`, stamp `acted`/`handled_at`) → apply the held-hide filter → `effective_tier`/`score` at read (unchanged) → rank → return. On a cold/expired miss: return empty **plus a `syncing` hint** so the client shows the sync UX and fires a refresh; the feed fills when the refresh lands (no slow read-through in the request path).
- **Refresh (`POST /feed/refresh`)** — the heavy path (connect + manual pull only): live-pull every provider (unchanged), classify (unchanged), then `HSET` each assembled row into `feed:{uid}` + reset TTL. Returns the same `RefreshResult` (+ `held`).
- **Webhook append** — `ingest → classify_item` writes the single row into `feed:{uid}` + resets TTL. Real-time-while-open; the next open re-pulls live regardless.
- **Actions** — `snooze`/`dismiss`/`mark_handled` write the ledger (durable) and update/evict the row in `feed:{uid}`. Read-time overlay is the safety net if the two diverge.
- **Disconnect (Cluster F)** — `HDEL` that source's fields from `feed:{uid}` + delete its `feed_actions` rows.

## Contract mapping (services barely change)

The `FeedRepository` Protocol is preserved; a new `RedisFeedRepository` implements it against Redis + the ledger. Method mapping:
- `upsert` / `apply_classification` / `mark_attempted` / `list_pending_classification` → Redis hash ops.
- `list_by_user` → `HGETALL` + ledger overlay (retention becomes the TTL; the deadline/assigned "never ages out" logic is moot since TTL is 24h and refresh re-populates).
- `mark_handled` / `snooze` → ledger writes (+ Redis row update).
- `purge_expired` → **removed** (TTL replaces it).
So `feed.py`, `classifier.py`, `sync.py`, `ingest.py` keep their contracts; only `composition.py` swaps the implementation and the ledger repo is injected.

## Concurrency hotfix (prerequisite, folds in here)

The `/feed` 500s Vicky saw (`httpx.ReadError: [Errno 11]`) are the single shared Supabase httpx client used concurrently across the request threadpool + classify/webhook pools. Redis-py needs a proper pool too. Fix both: a connection pool for Redis and a per-thread / pooled Supabase client for the durable reads. (The Later-401 token-refresh hotfix is client-side and lands with the UX phase, but can go first — it is independent.)

## Deployment

- **Box prerequisite:** install Docker (`sudo dnf install -y docker && sudo systemctl enable --now docker`) or use preinstalled `podman`. Then:
  `docker run -d --name redis --restart unless-stopped -p 127.0.0.1:6379:6379 redis:7 redis-server --maxmemory 512mb --maxmemory-policy volatile-lru` — no volume, so a restart cold-starts (accepted).
- **Backend dep:** add `redis` to the project deps (`uv add redis`).
- **Config:** `REDIS_URL=redis://127.0.0.1:6379/0` in `.env`; `composition.py` builds `RedisFeedRepository` when set, else falls back to the in-memory repo for tests/local.
- **Cutover:** dev only, near-zero data; migration 0010 drops `feed_items`, adds `feed_actions`. Switch composition, deploy, verify live via the logging + browser loop.

## Frontend delta (feeds the UX phase)

- **Syncing-over-cache**: Day + To-dos + Later show a "syncing latest" indicator (same language as the connect pill) whenever a live fetch/refresh is running over the cached rows, so stale-then-fresh never looks broken. Activity stays deprioritized.
- **Refresh button** on Day / To-dos / Later → fires `/feed/refresh` for all integrations + re-streams Later, showing loading over the cached data.
- Clusters A/B/D/E from the UX plan are unchanged; Cluster F now means Redis+ledger deletion.

## Build order

1. **Hotfixes**: Supabase-client concurrency (`/feed` 500) + Later-stream 401. Deploy, verify.
2. **Redis store**: `RedisFeedRepository` + `feed_actions` ledger + migration 0010 + composition swap + Redis container on the box. RGR at the repo contract. Deploy, verify a full connect→refresh→webhook→dismiss cycle live.
3. **UX**: syncing-over-cache + refresh button + Clusters A/B/D/E/F.

## Open decisions

1. **Cold-miss read** returns empty + syncing (client then refreshes), rather than a slow synchronous read-through (~40s Gmail). Confirm.
2. **`maxmemory` cap** — 512mb to start (tune later)? 
3. **`cls:{content_hash}` cross-item cache** — include now or defer? (Recommend defer.)
4. **Docker vs podman** on the box — Docker install (needs the one-time `dnf install`) or use podman if present?
