-- The "attempted" marker for classification.
--
-- Three visible states for an item the rules deferred to the model, told apart
-- by this column, not by ``llm_tier is null`` alone:
--   held    : needs_llm, no llm_tier, llm_attempted_at IS NULL  -> hidden
--   failed  : needs_llm, no llm_tier, llm_attempted_at IS NOT NULL -> shown at ceiling
--   done    : llm_tier IS NOT NULL -> shown at the clamped model tier
-- Without it a held item and a failed one are byte-identical, so a model outage
-- would either hide every LLM item or defeat the hold entirely.
alter table public.feed_items
  add column if not exists llm_attempted_at timestamptz;

-- Rollout backfill (H2). The moment the read-time held filter ships, every
-- existing row that still owes the model a verdict would either vanish or
-- mis-band. Two corrections, in order:

-- 1) Linear is now deterministic (priority ignored, due date decides at read
--    time). Its old per-priority signals were Banded (needs_llm=true); normalise
--    them to the single ``linear`` signal and stop them queueing for the model.
update public.feed_items
   set signal = 'linear',
       needs_llm = false
 where source = 'linear';

-- 2) Grandfather every remaining pre-deploy held row as attempted, so it stays
--    visible (at its band ceiling) instead of disappearing until re-judged. The
--    next synchronous refresh reclassifies these into their real tiers.
update public.feed_items
   set llm_attempted_at = now()
 where needs_llm = true
   and llm_tier is null
   and llm_attempted_at is null;
