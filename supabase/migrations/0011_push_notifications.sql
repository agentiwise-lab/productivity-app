-- Push notifications: the stored preference, and where to reach each device.
--
-- Both halves of making the You tab's "Notify me" control real. Until now it
-- was local component state that reset on every launch and drove nothing.

-- The preference. Default 'urgent' rather than 'off': a new account is opted
-- in at the narrowest setting, because off-by-default makes the feature
-- invisible and anything wider buzzes about things nobody asked for.
--
-- The check is added separately rather than inline. Postgres has no
-- `add constraint if not exists`, so an inline check on a re-run of
-- `add column if not exists` fails the whole file, and this migration is
-- applied unattended.
alter table public.users
  add column if not exists notify_level text not null default 'urgent';

alter table public.users
  drop constraint if exists users_notify_level_check;
alter table public.users
  add constraint users_notify_level_check
  check (notify_level in ('urgent', 'urgent_today', 'all', 'off'));

-- Where to reach each device.
--
-- The Expo token is the primary key, not a surrogate id. A token identifies a
-- *device*, and a device can change hands: sign out on a phone, sign in as
-- somebody else. Making it the key means the owning account is a value to
-- overwrite (see the repository's upsert) rather than a second row, so the
-- same phone can never carry two live claims and start delivering one person's
-- work to another.
create table if not exists public.device_tokens (
  token        text primary key,
  user_id      uuid not null references public.users(id) on delete cascade,
  platform     text not null check (platform in ('ios', 'android')),
  created_at   timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

-- The only read is "every device for this user", at send time.
create index if not exists device_tokens_user_id_idx
  on public.device_tokens (user_id);

-- Service role bypasses RLS; enabling it with no policy denies anon and
-- authenticated, which is what every other table does (migration 0005). A push
-- token is a send-anything-to-this-device capability, so it belongs with the
-- credential tables rather than with the feed.
alter table public.device_tokens enable row level security;
revoke all on public.device_tokens from anon, authenticated;
