from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITIES_JS = (ROOT / "web" / "opportunities.js").read_text(encoding="utf-8")


def test_opportunity_date_formatter_uses_valid_intl_options():
    assert "dateStyle:'medium', timeStyle:'short', timeZoneName:'short'" not in OPPORTUNITIES_JS
    assert "year:'numeric', month:'short', day:'numeric'" in OPPORTUNITIES_JS
    assert "hour:'2-digit', minute:'2-digit', timeZoneName:'short'" in OPPORTUNITIES_JS


def test_feed_status_render_isolated_after_successful_retrieval():
    assert "renderStep('feed-status'" in OPPORTUNITIES_JS
    assert "gfiTrack('feed_ready'" in OPPORTUNITIES_JS
