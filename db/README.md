# GFI evaluation & monitoring database

The public site emits privacy-bounded, anonymous usage events to Supabase using
the **publishable (anon) key only**. This directory holds the schema, row-level
security, owner-only aggregate views, and the server-side reporting functions the
monitoring automation uses. Nothing here is a secret; the only powerful
credential (`service_role`) lives **only** in GitHub Actions secrets and is never
placed in `web/`.

## Apply order (run once, and after any change below)

Apply these in the Supabase SQL editor (or `supabase db push`) **in this order** —
later files depend on earlier ones:

1. `supabase_evaluation.sql` — `gfi_usage_events`, `gfi_usefulness_pulse`, RLS, insert policies, indexes.
2. `application_journey_v1.sql` — `gfi_application_journey_events`, RLS, `private` funnel/outcome/conversion views.
3. `supabase_owner_dashboard.sql` — `private.gfi_usage_daily`, `gfi_pulse_overall`, `gfi_pulse_segments`.
4. `gfi_reporting_functions.sql` — `public.gfi_ingestion_health()` and `public.gfi_owner_report(int)` (SECURITY DEFINER, `service_role`-only).

All statements are idempotent (`create ... if not exists` / `create or replace`),
so re-running the whole set in order is safe.

## Verify it is live (2 minutes)

1. In the SQL editor: `select public.gfi_ingestion_health();` — you should get a
   JSON object. `events_24h` will be 0 until real traffic arrives, but the call
   itself must succeed (proves the functions and tables exist).
2. In a browser on the live site, open DevTools → Network, reload, and confirm
   the `POST …/rest/v1/gfi_usage_events` returns **201**. Anything else:
   - **401 / 403** → policies/grants not applied (re-run step 1 of the apply order).
   - **404** → table or project missing (project paused, or wrong ref/key).
   - **no request at all** → the surface being used is not loading `opportunities.js`
     (e.g. a Wix embed serving the telemetry-free `wix-bundle.html` instead of
     iframing the Pages site).

## Secrets for the monitoring automation (GitHub → Settings → Secrets → Actions)

The health probe and owner report run server-side and need:

- `SUPABASE_URL` — e.g. `https://<ref>.supabase.co`
- `SUPABASE_SERVICE_ROLE_KEY` — the project's service-role key.

**Never** add the service-role key to any file under `web/`. A test
(`tests/test_observability.py`) fails the build if it ever appears there.
Both workflows skip cleanly when the secrets are absent, so merging this without
the secrets set will not produce failing runs.

## What reads what

```
ingestion-health probe  →  public.gfi_ingestion_health()   (alert if no events in 7d)
owner-report generator  →  public.gfi_owner_report(30)      (renders a private HTML dashboard artifact)
owner ad-hoc SQL        →  private.gfi_* views              (direct in the Supabase SQL editor)
browser (anon key)      →  INSERT only, no SELECT           (cannot read anything back)
```

## Privacy invariants (do not weaken)

- No SELECT policy for `anon`/`authenticated` on any table.
- `private` schema revoked from `public`/`anon`/`authenticated`.
- Segment views suppress cells with fewer than 5 responses.
- Events carry no visitor id, session id, IP, or fingerprint; the pulse asks for
  no name, email, or sensitive identity attributes.
