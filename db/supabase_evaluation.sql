-- Global Funding Intelligence evaluation store
-- Apply in Supabase SQL editor. Browser uses only the publishable/anon key.

create extension if not exists pgcrypto;

create table if not exists public.gfi_usage_events (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  event_name text not null check (event_name in (
    'page_ready','feed_ready','feed_unavailable','filter_change',
    'search_used','profile_ranked','primary_source_open','pulse_submitted'
  )),
  page text not null default 'global-funding-intelligence',
  embedded boolean not null default true,
  language text,
  viewport text check (viewport in ('mobile','tablet','desktop')),
  properties jsonb not null default '{}'::jsonb
);

create table if not exists public.gfi_usefulness_pulse (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  country_code text check (country_code is null or country_code ~ '^[A-Z]{2}$'),
  world_region text,
  organisation_type text,
  career_stage text,
  sector text,
  setting_identity text check (setting_identity in ('global_majority','high_income','prefer_not_to_say','unsure')),
  found_relevant_opportunity boolean,
  usefulness smallint check (usefulness between 1 and 5),
  would_return boolean,
  comment text check (comment is null or char_length(comment) <= 500)
);

alter table public.gfi_usage_events enable row level security;
alter table public.gfi_usefulness_pulse enable row level security;

revoke all on public.gfi_usage_events from anon, authenticated;
revoke all on public.gfi_usefulness_pulse from anon, authenticated;
grant insert on public.gfi_usage_events to anon, authenticated;
grant insert on public.gfi_usefulness_pulse to anon, authenticated;

create policy "public insert usage events"
on public.gfi_usage_events
for insert
to anon, authenticated
with check (
  event_name in ('page_ready','feed_ready','feed_unavailable','filter_change','search_used','profile_ranked','primary_source_open','pulse_submitted')
  and page = 'global-funding-intelligence'
  and jsonb_typeof(properties) = 'object'
);

create policy "public insert usefulness pulse"
on public.gfi_usefulness_pulse
for insert
to anon, authenticated
with check (
  (country_code is null or country_code ~ '^[A-Z]{2}$')
  and (usefulness is null or usefulness between 1 and 5)
  and (comment is null or char_length(comment) <= 500)
);

-- No SELECT policy is granted to anon/authenticated. Public clients can submit but cannot read responses.
-- Owner/admin analysis should use Supabase dashboard or a protected server-side credential.

create index if not exists gfi_usage_events_created_at_idx on public.gfi_usage_events(created_at desc);
create index if not exists gfi_usage_events_event_name_idx on public.gfi_usage_events(event_name);
create index if not exists gfi_usefulness_pulse_created_at_idx on public.gfi_usefulness_pulse(created_at desc);
create index if not exists gfi_usefulness_pulse_country_idx on public.gfi_usefulness_pulse(country_code);
