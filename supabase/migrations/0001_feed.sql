-- Feed schema. Section 5 of docs/mvp-plan.md.
--
-- Every table is keyed by user_id and carries an RLS policy of
-- user_id = auth.uid(). The backend reaches Postgres with the service role,
-- which bypasses RLS, so isolation is enforced twice: once in the repository
-- (every query is scoped) and once here, for anything that ever talks to the
-- database with a user's own JWT. A leak between users is the one bug this
-- product cannot survive, so it gets two independent guards.
--
-- There is deliberately no `tier` column. The tier the user sees is computed on
-- every read from rule_tier, llm_tier and the current clock. A stored tier
-- would keep claiming yesterday's urgency (plan 3.8).

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------- users

create table if not exists public.users (
  id                  uuid primary key references auth.users (id) on delete cascade,
  email               text        not null,
  timezone            text        not null default 'UTC',
  expo_push_token     text,
  working_hours_start time        not null default '09:00',
  working_hours_end   time        not null default '18:00',
  created_at          timestamptz not null default now()
);

-- ---------------------------------------------------------- connections

create type connection_status as enum ('active', 'expired', 'revoked', 'error');

create table if not exists public.connections (
  id                            uuid primary key default gen_random_uuid(),
  user_id                       uuid not null references public.users (id) on delete cascade,
  provider                      text not null,          -- 'github' | 'slack' | ...
  composio_connected_account_id text not null,
  composio_user_id              text not null,
  status                        connection_status not null default 'active',
  -- Identity on the provider, resolved once at connection time (plan 3.10).
  -- Without these, "is this my PR" and Slack mention detection cannot run.
  provider_login                text,
  provider_user_id              text,
  connected_at                  timestamptz not null default now(),
  last_event_at                 timestamptz,
  unique (user_id, provider)
);

-- ------------------------------------------------------------ feed_items

create type feed_tier   as enum ('urgent', 'today', 'can_wait', 'noise');
create type feed_status as enum ('unread', 'acted', 'dismissed', 'snoozed');
create type tier_source as enum ('rule', 'llm');

create table if not exists public.feed_items (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null references public.users (id) on delete cascade,
  source        text not null,
  source_ref    text not null,

  -- Judgement, stored. Kept apart on purpose: the rules answer instantly so the
  -- feed renders at once, and the model's verdict lands later (plan 4.4).
  rule_tier     feed_tier   not null,
  llm_tier      feed_tier,
  tier_source   tier_source not null default 'rule',
  type_tag      text        not null default 'fyi',
  needs_llm     boolean     not null default false,

  -- Card content. Every one of these appears on the card (plan 6.1).
  title         text not null,
  summary       text,
  reason        text,
  url           text not null,
  repo          text not null default '',
  context_chip  text,
  sender_name   text,
  sender_handle text,
  actors        jsonb not null default '[]'::jsonb,

  deadline      timestamptz,
  occurred_at   timestamptz,          -- the source's clock, what ranking uses
  created_at    timestamptz not null default now(),  -- ours, when we ingested
  snoozed_until timestamptz,
  handled_at    timestamptz,

  is_blocking   boolean not null default false,
  status        feed_status not null default 'unread',
  content_hash  text,
  raw           jsonb not null default '{}'::jsonb,

  unique (user_id, source_ref)
);

-- The feed read: one user's live items, newest first.
create index if not exists feed_items_live_idx
  on public.feed_items (user_id, occurred_at desc)
  where status = 'unread';

-- The classification queue.
create index if not exists feed_items_pending_llm_idx
  on public.feed_items (user_id)
  where needs_llm and llm_tier is null;

-- ------------------------------------------------------ user_preferences

create type notify_level as enum ('urgent', 'urgent_today', 'off');

create table if not exists public.user_preferences (
  user_id          uuid primary key references public.users (id) on delete cascade,
  notify_level     notify_level not null default 'urgent',
  muted_repos      text[] not null default '{}',
  muted_channels   text[] not null default '{}',
  vip_actors       text[] not null default '{}',
  priority_repos   text[] not null default '{}',
  -- Per source: do not send this source's content to the model (plan 4.4).
  -- Classifying text means sending it to a third party, so the user gets a
  -- switch rather than a footnote.
  ai_content_optout jsonb not null default '{}'::jsonb
);

-- ---------------------------------------------------------------- actions

create table if not exists public.actions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references public.users (id) on delete cascade,
  feed_item_id uuid references public.feed_items (id) on delete set null,
  type         text not null,
  payload      jsonb not null default '{}'::jsonb,
  result       jsonb,
  performed_at timestamptz not null default now()
);

create index if not exists actions_user_idx on public.actions (user_id, performed_at desc);

-- -------------------------------------------------------------- llm_cache

-- Keyed on the content, not the item reference: a thread keeps one source_ref
-- while its content changes underneath, so a reference-keyed cache would serve
-- a stale verdict forever. Not user-scoped, because the same content classifies
-- the same way for anyone; it holds no user identifiers.
create table if not exists public.llm_cache (
  content_hash text primary key,
  tier         feed_tier not null,
  summary      text not null,
  reason       text not null,
  model        text not null,
  created_at   timestamptz not null default now()
);

-- -------------------------------------------------------------------- RLS

alter table public.users            enable row level security;
alter table public.connections      enable row level security;
alter table public.feed_items       enable row level security;
alter table public.user_preferences enable row level security;
alter table public.actions          enable row level security;

create policy users_own_row on public.users
  for all using (id = auth.uid()) with check (id = auth.uid());

create policy connections_own_rows on public.connections
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy feed_items_own_rows on public.feed_items
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy user_preferences_own_rows on public.user_preferences
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy actions_own_rows on public.actions
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- llm_cache is left without RLS on purpose: it is content-addressed and holds
-- no user identifiers. It is never exposed to the anon role.
revoke all on public.llm_cache from anon, authenticated;
