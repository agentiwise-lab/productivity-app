-- The canonical classification signal (e.g. "slack_dm", "linear_due").
-- Stored so the tier band — the floor/ceiling the model's rating is clamped to
-- at read time — can be recovered from the row. Nullable: legacy rows read as an
-- unclamped band, which is exactly the pre-band behaviour.
alter table public.feed_items add column if not exists signal text;
