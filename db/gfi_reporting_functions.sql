-- Global Funding Intelligence — server-side reporting functions.
--
-- These are the ONLY sanctioned way for automation (the ingestion-health probe
-- and the owner-report generator) to read aggregates over the REST API. They are
-- SECURITY DEFINER so they can read the locked-down `private` schema, and EXECUTE
-- is granted to `service_role` only. They never return row-level data, only
-- aggregates that already exist in the private views (which apply the >=5
-- suppression). Apply AFTER supabase_evaluation.sql, application_journey_v1.sql
-- and supabase_owner_dashboard.sql (they depend on those tables and views).
--
-- Nothing here is callable by the browser: anon/authenticated have no EXECUTE.

-- Fast health summary for the scheduled ingestion probe.
create or replace function public.gfi_ingestion_health()
returns jsonb
language sql
security definer
set search_path = public, pg_temp
as $$
  select jsonb_build_object(
    'generated_at', now(),
    'last_event_at', (select max(created_at) from public.gfi_usage_events),
    'events_24h', (select count(*) from public.gfi_usage_events where created_at >= now() - interval '24 hours'),
    'events_7d', (select count(*) from public.gfi_usage_events where created_at >= now() - interval '7 days'),
    'pulse_7d', (select count(*) from public.gfi_usefulness_pulse where created_at >= now() - interval '7 days'),
    'journeys_7d', (select count(distinct journey_id) from public.gfi_application_journey_events where created_at >= now() - interval '7 days')
  );
$$;

revoke all on function public.gfi_ingestion_health() from public, anon, authenticated;
grant execute on function public.gfi_ingestion_health() to service_role;

-- One-call owner report: every aggregate the dashboard needs, in a single JSON
-- payload. Reads the existing private views so suppression rules are inherited.
create or replace function public.gfi_owner_report(p_days integer default 30)
returns jsonb
language sql
security definer
set search_path = public, private, pg_temp
as $$
  select jsonb_build_object(
    'generated_at', now(),
    'window_days', p_days,
    -- Be explicit about what each section covers. Usage events are windowed by
    -- p_days; the feedback (pulse) and application-journey aggregates read the
    -- cumulative private views, so they are all-time, not windowed. Counts are
    -- event counts, never unique visitors: no visitor/session id is collected,
    -- so users cannot be de-duplicated.
    'windows', jsonb_build_object(
      'usage', 'last ' || p_days || ' days',
      'feedback', 'cumulative (all responses to date)',
      'journey', 'cumulative (all journeys to date)',
      'basis', 'event counts, not unique visitors'
    ),
    'ingestion', public.gfi_ingestion_health(),
    'usage_daily', (
      select coalesce(jsonb_agg(jsonb_build_object(
        'date', report_date, 'event', event_name, 'count', event_count
      ) order by report_date, event_name), '[]'::jsonb)
      from private.gfi_usage_daily
      where report_date >= current_date - p_days
    ),
    'usage_totals', (
      select coalesce(jsonb_object_agg(event_name, total), '{}'::jsonb)
      from (
        select event_name, sum(event_count)::bigint as total
        from private.gfi_usage_daily
        where report_date >= current_date - p_days
        group by event_name
      ) t
    ),
    'pulse_overall', (select coalesce(to_jsonb(p), '{}'::jsonb) from private.gfi_pulse_overall p),
    'pulse_segments', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from private.gfi_pulse_segments s),
    'application_funnel', (select coalesce(jsonb_agg(to_jsonb(f) order by f.journeys desc), '[]'::jsonb) from private.gfi_application_funnel f),
    'application_outcomes', (select coalesce(jsonb_agg(to_jsonb(o)), '[]'::jsonb) from private.gfi_application_outcomes o),
    'source_conversion', (select coalesce(jsonb_agg(to_jsonb(sc) order by sc.journeys desc), '[]'::jsonb) from private.gfi_application_source_conversion sc)
  );
$$;

revoke all on function public.gfi_owner_report(integer) from public, anon, authenticated;
grant execute on function public.gfi_owner_report(integer) to service_role;
