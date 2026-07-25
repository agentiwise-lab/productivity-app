-- Display name. Optional: a user has an account before they have a name, and
-- the greeting and You tab fall back gracefully when it is null. Set through
-- PATCH /me; never touched by the auth flow, which only owns credentials.
alter table public.users add column if not exists name text;
