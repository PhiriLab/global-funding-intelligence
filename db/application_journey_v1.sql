create table if not exists public.gfi_application_journey_events (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  journey_id uuid not null,
  opportunity_key text not null check (char_length(opportunity_key) between 1 and 300),
  source_id text check (source_id is null or char_length(source_id) <= 100),
  stage text not null check (stage in ('discovered','saved','eligibility_checked','partner_building','decision_to_apply','drafting','internal_review','submitted','interview_rebuttal','awarded','unsuccessful','withdrawn','pending','not_disclosed')),
  role text check (role is null or role in ('lead','partner','unknown','not_disclosed')),
  outcome text check (outcome is null or outcome in ('awarded','unsuccessful','withdrawn','pending','not_disclosed')),
  gfi_helped_discover boolean,
  gfi_helped_assess boolean,
  award_value_band text check (award_value_band is null or award_value_band in ('under_50k','50k_249k','250k_999k','1m_plus','not_disclosed')),
  schema_version smallint not null default 1 check (schema_version = 1)
);

alter table public.gfi_application_journey_events enable row level security;
revoke all on public.gfi_application_journey_events from anon, authenticated;
grant insert on public.gfi_application_journey_events to anon, authenticated;

drop policy if exists "public_insert_application_journey" on public.gfi_application_journey_events;
create policy "public_insert_application_journey"
on public.gfi_application_journey_events
for insert
to anon, authenticated
with check (true);

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;

create or replace view private.gfi_application_funnel
with (security_invoker = true)
as
select stage, count(distinct journey_id)::bigint as journeys
from public.gfi_application_journey_events
group by stage;

create or replace view private.gfi_application_outcomes
with (security_invoker = true)
as
select outcome, count(distinct journey_id)::bigint as journeys
from public.gfi_application_journey_events
where outcome is not null
group by outcome;

create or replace view private.gfi_application_source_conversion
with (security_invoker = true)
as
select source_id,
       count(distinct journey_id)::bigint as journeys,
       count(distinct journey_id) filter (where stage = 'submitted')::bigint as submitted,
       count(distinct journey_id) filter (where outcome = 'awarded')::bigint as awarded
from public.gfi_application_journey_events
where source_id is not null
group by source_id
having count(distinct journey_id) >= 5;
