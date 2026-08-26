"""Per-funder attribution and reach signal.

The sponsor use-case reports need usage attributed to a specific funder ("what
happened in relation to your calls"). Two things must hold: every funder link
carries its source_id (so click-throughs are not recorded as 'unknown'), and a
deduped 'source_impression' fires when a funder's card is seen (so reports can
quantify the reach the platform delivers to a funder). The event is gated in the
client allow-set AND in the database (CHECK constraint + RLS policy); all must
agree or inserts are silently rejected.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
DB = Path(__file__).resolve().parents[1] / "db"
APP_JS = (WEB / "app.js").read_text(encoding="utf-8")
OPPS_JS = (WEB / "opportunities.js").read_text(encoding="utf-8")
EVAL_SQL = (DB / "supabase_evaluation.sql").read_text(encoding="utf-8")


def test_funder_directory_links_carry_source_id():
    # Directory click-throughs must attribute to the funder, not fall back to 'unknown'.
    assert 'class="source-link" data-source-id="${escapeHTML(s.id)}"' in APP_JS


def test_directory_rewires_telemetry_after_rerender():
    # Filter/search re-renders replace the cards; the new links must be (re)wired.
    assert "typeof wireSourceLinkTelemetry==='function'" in APP_JS
    assert "wireSourceLinkTelemetry()" in APP_JS


def test_impression_event_is_deduped_and_privacy_safe():
    assert "gfiTrack('source_impression', {source_id:" in OPPS_JS
    assert "IntersectionObserver" in OPPS_JS
    assert "gfiSeenImpressions" in OPPS_JS          # deduped per funder per load
    assert "sourceId === 'unknown'" in OPPS_JS      # never attribute an impression to 'unknown'
    # Impressions run through the same DNT-guarded, allowlisted sender.
    assert "gfiWatchImpression" in OPPS_JS


def test_source_impression_is_allowed_everywhere_or_nowhere():
    # Client allow-set, DB CHECK constraint, and DB RLS policy must all include it.
    assert "'source_impression'" in OPPS_JS
    assert EVAL_SQL.count("'source_impression'") >= 2  # CHECK constraint + RLS with-check
    # And it must sit inside both event_name lists, not merely appear in a comment.
    assert "'primary_source_open','pulse_submitted','source_impression'" in EVAL_SQL
