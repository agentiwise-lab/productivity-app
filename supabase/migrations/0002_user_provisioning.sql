-- Mirror auth.users into public.users, and give every user their preferences.
--
-- Without this, signing in with a magic link creates an auth.users row and
-- nothing else, so the very first feed_items insert fails on a foreign key and
-- the app is dead on arrival for a brand new account. Found by probing the
-- live database rather than by reading the schema: the FK chain
-- feed_items -> public.users -> auth.users has no automatic first link.
--
-- security definer is required: the trigger runs as the signing-up user, who
-- has no rights on public.users. search_path is pinned because a definer
-- function that resolves names through a caller-controlled path is a
-- privilege-escalation route.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email)
  values (new.id, coalesce(new.email, ''))
  on conflict (id) do nothing;

  insert into public.user_preferences (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
