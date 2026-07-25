-- Self-owned authentication: the backend, not Supabase Auth, owns identity.
--
-- Until now public.users.id referenced auth.users(id) and a GoTrue trigger
-- (0002) mirrored new auth users into public.users. We are dropping that: the
-- app owns OTP, password hashing, and JWT minting, and Supabase is storage
-- only. This keeps the door open to another Postgres provider later, since
-- nothing here depends on auth.* any more.
--
-- The id column, its type, its values, and every inbound FK from feed_items /
-- connections / user_preferences / actions are preserved. Only the *inbound*
-- FK from public.users.id -> auth.users(id) is dropped, so existing rows and
-- their children survive untouched.

-- 1. Sever the GoTrue link. The trigger and its function came from 0002; the
--    FK was created inline in 0001 and Postgres named it users_id_fkey.
drop trigger if exists on_auth_user_created on auth.users;
drop function if exists public.handle_new_user();
alter table public.users drop constraint if exists users_id_fkey;

-- 2. Own the id now that auth.users no longer supplies it, and hold the
--    password. Null until the user completes signup and sets one; a row can
--    exist (e.g. a half-finished provisioning) without a usable credential.
alter table public.users alter column id set default gen_random_uuid();
alter table public.users add column if not exists password_hash text;

-- 3. OTP challenges, hashed at rest. purpose keeps a signup code from being
--    spent as a reset code and vice-versa. The partial unique index makes
--    "one live challenge per (email, purpose)" a database invariant: send
--    upserts onto it, verify/consume reads and closes it.
create type otp_purpose as enum ('signup', 'reset');

create table if not exists public.email_otps (
  id            uuid primary key default gen_random_uuid(),
  email         text        not null,
  purpose       otp_purpose not null,
  code_hash     text        not null,
  expires_at    timestamptz not null,
  attempts      int         not null default 0,
  consumed_at   timestamptz,
  last_sent_at  timestamptz not null default now(),
  created_at    timestamptz not null default now()
);

create unique index if not exists email_otps_active_idx
  on public.email_otps (email, purpose)
  where consumed_at is null;

-- 4. Refresh tokens, stored only as a hash, with rotation lineage. A presented
--    token that is already revoked is a reuse signal (theft): the service
--    revokes the whole family. rotated_from records which token minted this one.
create table if not exists public.refresh_tokens (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users (id) on delete cascade,
  token_hash   text not null unique,
  expires_at   timestamptz not null,
  revoked_at   timestamptz,
  rotated_from uuid references public.refresh_tokens (id),
  created_at   timestamptz not null default now()
);

create index if not exists refresh_tokens_user_idx on public.refresh_tokens (user_id);
