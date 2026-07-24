-- The message itself.
--
-- ``SupabaseFeedRepository`` has always written a ``body`` column, and
-- ``0001_feed.sql`` never created one. Every insert against the live project
-- therefore failed with PGRST204 ("Could not find the 'body' column"), and the
-- failure was per-row and caught, so a refresh reported success while storing
-- nothing: sixty items fetched, zero persisted, an empty feed and no error.
--
-- The detail sheet renders this, and the classifier reads it to judge the tier,
-- so a feed item without it is a title and nothing else.
--
-- Additive and idempotent: no rewrite of existing rows, safe to re-run.

alter table public.feed_items
  add column if not exists body text;

-- Retention keeps an open item with a deadline regardless of its age, so the
-- read path filters on ``deadline is not null`` alongside ``occurred_at``.
-- Without this index that clause forces a sequential scan of the table.
create index if not exists feed_items_deadline_idx
  on public.feed_items (user_id, deadline)
  where deadline is not null;
