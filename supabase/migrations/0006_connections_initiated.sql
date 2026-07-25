-- A connection has a life before it is active: the user has been sent to the
-- provider's consent screen but has not finished. Without a value for that
-- state, a pending row is indistinguishable from a working one, and the poll
-- that waits for ACTIVE has nowhere to record that it is still waiting.
--
-- 'initiated' is added to the existing connection_status enum (0001). Postgres
-- adds an enum value in its own transaction, so this runs alone.

alter type connection_status add value if not exists 'initiated';
