-- 0010: move the feed into Redis; keep only the durable action ledger.
--
-- The feed content and the model's verdict now live in Redis (ephemeral, 24h
-- TTL). The one thing that must survive an eviction or a Redis restart is what
-- the user did to an item, keyed on (user_id, source_ref) so it stays valid
-- across a re-ingest that mints a fresh Redis row.

create table if not exists public.feed_actions (
  user_id uuid not null,
  source_ref text not null,
  status text not null default 'unread',
  snoozed_until timestamptz,
  handled_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (user_id, source_ref)
);

-- Service role bypasses RLS; enabling it with no policy denies anon/auth, which
-- matches every other table (migration 0005).
alter table public.feed_actions enable row level security;

-- Backfill any user state worth keeping from the table we are about to drop.
insert into public.feed_actions
  (user_id, source_ref, status, snoozed_until, handled_at, updated_at)
select user_id, source_ref, status, snoozed_until, handled_at, now()
from public.feed_items
where status <> 'unread' or snoozed_until is not null or handled_at is not null
on conflict (user_id, source_ref) do nothing;

-- Drop the FK explicitly (not via CASCADE) before removing the table, so the
-- audit rows in public.actions keep their feed_item_id as a plain value.
alter table public.actions drop constraint if exists actions_feed_item_id_fkey;

drop table if exists public.feed_items;
