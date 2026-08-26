#!/usr/bin/env python3
"""Owner-only GFI usage & impact dashboard generator.

Reads aggregate-only data from the Supabase SECURITY DEFINER function
`public.gfi_owner_report(int)` using the server-side service-role key (never the
browser key), and renders a self-contained HTML dashboard plus a JSON snapshot.

Design goals:
- No third-party analytics vendor; Supabase is the only backend.
- Aggregates only. The function never returns row-level data, and segment views
  already suppress cells with fewer than 5 responses.
- `render_report(payload)` is pure and offline-testable; `main()` does the I/O.

Usage:
  SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python scripts/owner_report.py \
      --days 30 --out-dir dist/owner-report
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def fetch_report(url: str, service_key: str, days: int, timeout: float = 30.0) -> dict:
    endpoint = url.rstrip("/") + "/rest/v1/rpc/gfi_owner_report"
    body = json.dumps({"p_days": days}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("gfi_owner_report did not return a JSON object")
    return payload


def _num(value, default=0):
    return value if isinstance(value, (int, float)) and value is not None else default


def _tile(label: str, value: str, note: str = "") -> str:
    note_html = f'<span class="note">{html.escape(note)}</span>' if note else ""
    return (
        f'<div class="tile"><span class="value">{html.escape(str(value))}</span>'
        f'<span class="label">{html.escape(label)}</span>{note_html}</div>'
    )


def render_report(payload: dict) -> str:
    """Pure renderer: aggregate payload -> self-contained HTML. No network."""
    generated = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    window_days = _num(payload.get("window_days"), 30)
    totals = payload.get("usage_totals") or {}
    ingestion = payload.get("ingestion") or {}
    pulse = payload.get("pulse_overall") or {}
    segments = payload.get("pulse_segments") or []
    funnel = payload.get("application_funnel") or []

    visits = int(_num(totals.get("page_ready")))
    source_opens = int(_num(totals.get("primary_source_open")))
    searches = int(_num(totals.get("search_used")))
    rankings = int(_num(totals.get("profile_ranked")))
    ctr = f"{(100 * source_opens / visits):.0f}%" if visits else "—"

    responses = int(_num(pulse.get("responses")))
    mean_use = pulse.get("mean_usefulness")
    mean_use_str = f"{mean_use}/5" if mean_use is not None else "—"
    return_pct = pulse.get("would_return_pct")
    return_str = f"{return_pct}%" if return_pct is not None else "—"
    relevant_pct = pulse.get("found_relevant_pct")
    relevant_str = f"{relevant_pct}%" if relevant_pct is not None else "—"
    gm_responses = int(_num(pulse.get("global_majority_responses")))

    windows = payload.get("windows") or {}
    usage_window = windows.get("usage") or f"last {window_days} days"
    feedback_window = windows.get("feedback") or "cumulative (all responses to date)"
    journey_window = windows.get("journey") or "cumulative (all journeys to date)"

    tiles = "".join([
        _tile("Page loads", f"{visits:,}", f"page_ready events · {usage_window} · not unique visitors"),
        _tile("Primary-source click-throughs", f"{source_opens:,}", f"{ctr} per page load · {usage_window}"),
        _tile("Opportunity searches", f"{searches:,}", f"search_used events · {usage_window}"),
        _tile("Profile rankings run", f"{rankings:,}", f"profile_ranked events · {usage_window}"),
        _tile("Usefulness responses", f"{responses:,}", f"anonymous pulse · {feedback_window}"),
        _tile("Mean usefulness", mean_use_str, "cumulative"),
        _tile("Would use again", return_str, "cumulative"),
        _tile("Found a relevant opportunity", relevant_str, "cumulative"),
        _tile("Global-Majority responses", f"{gm_responses:,}", "self-identified · cumulative"),
    ])

    event_rows = "".join(
        f"<tr><td>{html.escape(str(name))}</td><td class='num'>{int(_num(count)):,}</td></tr>"
        for name, count in sorted(totals.items(), key=lambda kv: -_num(kv[1]))
    ) or "<tr><td colspan='2'>No events recorded in this window.</td></tr>"

    seg_rows = "".join(
        f"<tr><td>{html.escape(str(s.get('dimension','')))}</td>"
        f"<td>{html.escape(str(s.get('value','')))}</td>"
        f"<td class='num'>{int(_num(s.get('responses'))):,}</td>"
        f"<td class='num'>{html.escape(str(s.get('mean_usefulness','—')))}</td></tr>"
        for s in segments
    ) or "<tr><td colspan='4'>No segment reaches the 5-response reporting threshold yet.</td></tr>"

    funnel_rows = "".join(
        f"<tr><td>{html.escape(str(f.get('stage','')))}</td>"
        f"<td class='num'>{int(_num(f.get('journeys'))):,}</td></tr>"
        for f in funnel
    ) or "<tr><td colspan='2'>No application-journey data yet.</td></tr>"

    last_event = ingestion.get("last_event_at") or "—"
    events_7d = int(_num(ingestion.get("events_7d")))
    health = "healthy" if events_7d > 0 else "no events in 7 days — check the pipeline"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GFI usage & impact — owner report</title>
<style>
 :root{{--bg:#f6f8f6;--card:#fff;--line:#dce6df;--text:#10231b;--muted:#5f746a;--accent:#123c2a}}
 body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--text);line-height:1.5}}
 header,main{{max-width:1040px;margin:0 auto;padding:24px}}
 h1{{margin:0 0 4px;font-size:1.6rem}} .sub{{color:var(--muted);margin:0}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:22px 0}}
 .tile{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;display:flex;flex-direction:column;gap:4px}}
 .tile .value{{font-size:1.7rem;font-weight:800;color:var(--accent)}}
 .tile .label{{font-size:.82rem;color:var(--muted)}} .tile .note{{font-size:.72rem;color:var(--muted)}}
 section{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:16px 0}}
 h2{{font-size:1.05rem;margin:0 0 10px}}
 table{{width:100%;border-collapse:collapse}} th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);font-size:.9rem}}
 td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
 .health{{display:inline-block;padding:4px 10px;border-radius:99px;font-size:.8rem;font-weight:700;background:#dff4e6;color:#175b32}}
 .health.warn{{background:#fff1c9;color:#77520a}}
 footer{{max-width:1040px;margin:0 auto;padding:24px;color:var(--muted);font-size:.8rem}}
</style></head>
<body>
<header>
  <h1>Global Funding Intelligence — usage &amp; impact</h1>
  <p class="sub">Owner-only report • generated {html.escape(str(generated))} • usage window: {html.escape(usage_window)} • feedback &amp; journey: cumulative</p>
  <p style="margin-top:10px"><span class="health {'' if events_7d>0 else 'warn'}">Ingestion: {html.escape(health)}</span>
     &nbsp;last event: {html.escape(str(last_event))}</p>
</header>
<main>
  <div class="grid">{tiles}</div>
  <section><h2>Usage events <span style="font-weight:400;color:var(--muted)">— {html.escape(usage_window)}</span></h2>
    <p class="sub" style="margin:0 0 10px">Counts are event occurrences, not unique visitors: no visitor or session identifier is collected, so people cannot be de-duplicated.</p>
    <table><thead><tr><th>Event</th><th class="num">Count</th></tr></thead><tbody>{event_rows}</tbody></table>
  </section>
  <section><h2>Reach &amp; equity segments <span style="font-weight:400;color:var(--muted)">— {html.escape(feedback_window)}, ≥5 responses only</span></h2>
    <table><thead><tr><th>Dimension</th><th>Value</th><th class="num">Responses</th><th class="num">Mean usefulness</th></tr></thead>
    <tbody>{seg_rows}</tbody></table>
  </section>
  <section><h2>Application journey funnel <span style="font-weight:400;color:var(--muted)">— {html.escape(journey_window)}</span></h2>
    <table><thead><tr><th>Stage</th><th class="num">Journeys (distinct)</th></tr></thead><tbody>{funnel_rows}</tbody></table>
  </section>
</main>
<footer>
  Aggregate, anonymous data only. No visitor identifiers, IP addresses, or sensitive
  attributes are collected or shown. Usage figures are event counts (page loads and
  interactions), not unique visitors or sessions. Feedback and journey figures are
  cumulative. Segment cells with fewer than five responses are suppressed. Suitable
  for sharing high-level figures with sponsors and collaborators.
</footer>
</body></html>"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate the GFI owner usage/impact report.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--out-dir", default="dist/owner-report")
    args = parser.parse_args(argv)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — skipping report generation.")
        return 0

    payload = fetch_report(url, key, args.days)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_report(payload), encoding="utf-8")
    (out_dir / "data.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"Owner report written to {out_dir}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
