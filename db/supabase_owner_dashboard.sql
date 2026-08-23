-- Owner-only evaluation reporting layer.
-- The private schema is not exposed to public browser clients.
-- Segment views suppress cells with fewer than 5 responses.

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace view private.gfi_usage_daily as
select
  (created_at at time zone 'Europe/London')::date as report_date,
  event_name,
  count(*)::bigint as event_count
from public.gfi_usage_events
group by 1, 2;

create or replace view private.gfi_pulse_overall as
select
  count(*)::bigint as responses,
  round(avg(usefulness)::numeric, 2) as mean_usefulness,
  count(*) filter (where found_relevant_opportunity is true)::bigint as found_relevant_count,
  round(100.0 * count(*) filter (where found_relevant_opportunity is true) / nullif(count(found_relevant_opportunity), 0), 1) as found_relevant_pct,
  count(*) filter (where would_return is true)::bigint as would_return_count,
  round(100.0 * count(*) filter (where would_return is true) / nullif(count(would_return), 0), 1) as would_return_pct,
  count(*) filter (where setting_identity = 'global_majority')::bigint as global_majority_responses
from public.gfi_usefulness_pulse;

create or replace view private.gfi_pulse_segments as
select 'world_region'::text as dimension, coalesce(world_region, 'Prefer not to say') as value,
       count(*)::bigint as responses, round(avg(usefulness)::numeric, 2) as mean_usefulness
from public.gfi_usefulness_pulse group by world_region having count(*) >= 5
union all
select 'country_code', coalesce(country_code, 'Prefer not to say'), count(*)::bigint, round(avg(usefulness)::numeric, 2)
from public.gfi_usefulness_pulse group by country_code having count(*) >= 5
union all
select 'organisation_type', coalesce(organisation_type, 'Prefer not to say'), count(*)::bigint, round(avg(usefulness)::numeric, 2)
from public.gfi_usefulness_pulse group by organisation_type having count(*) >= 5
union all
select 'career_stage', coalesce(career_stage, 'Prefer not to say'), count(*)::bigint, round(avg(usefulness)::numeric, 2)
from public.gfi_usefulness_pulse group by career_stage having count(*) >= 5
union all
select 'sector', coalesce(sector, 'Prefer not to say'), count(*)::bigint, round(avg(usefulness)::numeric, 2)
from public.gfi_usefulness_pulse group by sector having count(*) >= 5
union all
select 'setting_identity', coalesce(setting_identity, 'prefer_not_to_say'), count(*)::bigint, round(avg(usefulness)::numeric, 2)
from public.gfi_usefulness_pulse group by setting_identity having count(*) >= 5;

revoke all on private.gfi_usage_daily from public, anon, authenticated;
revoke all on private.gfi_pulse_overall from public, anon, authenticated;
revoke all on private.gfi_pulse_segments from public, anon, authenticated;
