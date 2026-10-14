"""Offline checks for the observability-recovery layer.

These do not touch the live Supabase project; they verify the repository
artefacts are internally consistent, privacy-safe, and render correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db"
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "scripts"))

import owner_report  # noqa: E402


def test_reporting_functions_are_service_role_only():
    sql = (DB / "gfi_reporting_functions.sql").read_text(encoding="utf-8")
    for fn in ("public.gfi_ingestion_health()", "public.gfi_owner_report(integer)"):
        assert f"grant execute on function {fn} to service_role;" in sql
        assert f"revoke all on function {fn} from public, anon, authenticated;" in sql
    # SECURITY DEFINER must pin search_path (no mutable-search-path injection).
    assert sql.count("security definer") == 2
    assert sql.count("set search_path") == 2


def test_reporting_functions_expose_no_row_level_data():
    sql = (DB / "gfi_reporting_functions.sql").read_text(encoding="utf-8").lower()
    # Owner report reads only the suppressed private views + counts, never raw rows.
    assert "private.gfi_usage_daily" in sql
    assert "private.gfi_pulse_overall" in sql
    assert "select * from public.gfi_usefulness_pulse" not in sql


def test_service_role_key_never_appears_in_web():
    for path in WEB.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert "service_role" not in text, f"service_role leaked into {path}"
            assert "sb_secret_" not in text, f"secret key leaked into {path}"


def _fixture_payload():
    return {
        "generated_at": "2026-08-23T00:00:00+00:00",
        "window_days": 30,
        "windows": {
            "usage": "last 30 days",
            "feedback": "cumulative (all responses to date)",
            "journey": "cumulative (all journeys to date)",
            "basis": "event counts, not unique visitors",
        },
        "ingestion": {"last_event_at": "2026-08-22T23:00:00+00:00", "events_7d": 812, "events_24h": 96},
        "usage_totals": {
            "page_ready": 1000, "primary_source_open": 250, "search_used": 300,
            "profile_ranked": 120, "feed_ready": 990,
        },
        "pulse_overall": {
            "responses": 42, "mean_usefulness": 4.2, "would_return_pct": 88.0,
            "found_relevant_pct": 76.0, "global_majority_responses": 25,
        },
        "pulse_segments": [
            {"dimension": "world_region", "value": "Africa", "responses": 18, "mean_usefulness": 4.4},
        ],
        "application_funnel": [
            {"stage": "saved", "journeys": 30}, {"stage": "submitted", "journeys": 6},
        ],
    }


def test_render_report_is_pure_and_contains_key_metrics():
    html = owner_report.render_report(_fixture_payload())
    assert "<!doctype html>" in html.lower()
    assert "1,000" in html          # page-load count
    assert "25%" in html            # click-through per page load (250/1000)
    assert "4.2/5" in html          # mean usefulness
    assert "Africa" in html         # segment surfaced
    assert "healthy" in html        # ingestion health badge


def test_render_report_terminology_is_exact_about_meaning():
    html = owner_report.render_report(_fixture_payload())
    # page_ready must not be labelled "Visits" (implies unique people we cannot dedupe).
    assert "Page loads" in html
    assert "Visits" not in html
    assert "not unique visitors" in html
    assert "per page load" in html
    # Windows are explicit and honest: usage windowed, feedback/journey cumulative.
    assert "last 30 days" in html
    assert "cumulative" in html


def test_render_report_handles_empty_payload_without_crashing():
    html = owner_report.render_report({})
    assert "<!doctype html>" in html.lower()
    assert "no events in 7 days" in html.lower()


def test_main_skips_without_secrets(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert owner_report.main(["--out-dir", str(tmp_path / "r")]) == 0
    assert not (tmp_path / "r" / "index.html").exists()


def test_workflows_are_valid_yaml_and_secret_gated():
    import importlib.util

    if importlib.util.find_spec("yaml") is None:
        return
    import yaml

    for name in ("analytics-health.yml", "owner-report.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        yaml.safe_load(text)
        assert "SUPABASE_SERVICE_ROLE_KEY" in text
        assert "skipping" in text.lower() or "hashFiles(" in text
