-- RLS after auth.users is gone.
--
-- The 0001 policies all authorised rows with `user_id = auth.uid()`. With no
-- auth.users and our own JWT, auth.uid() resolves to null, so those policies
-- would deny everyone except the service role, which bypasses RLS anyway. They
-- are dead references, not protection. Drop them, but keep RLS *enabled* so any
-- accidental anon / authenticated client is denied by default (no policy = no
-- access). Real isolation is enforced in the repositories, which scope every
-- query by user_id exactly as supabase_feed_repository.py already documents.

drop policy if exists users_own_row            on public.users;
drop policy if exists connections_own_rows     on public.connections;
drop policy if exists feed_items_own_rows      on public.feed_items;
drop policy if exists user_preferences_own_rows on public.user_preferences;
drop policy if exists actions_own_rows         on public.actions;

-- The credential tables are never touched by a browser client. Enable RLS with
-- no policies (deny-all to anon/authenticated) and revoke table privileges so
-- only the service role, which the backend uses, can read them.
alter table public.email_otps     enable row level security;
alter table public.refresh_tokens enable row level security;
revoke all on public.email_otps     from anon, authenticated;
revoke all on public.refresh_tokens from anon, authenticated;
