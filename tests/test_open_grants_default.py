"""The opportunity feed is a discovery surface for grants you can still apply for.

It previously defaulted the Lifecycle filter to "all", which explicitly includes
"closed", so expired calls were shown as if they were live. Worse, nothing checked
closing_at, so a record still labelled 'open' with a deadline in the past rendered
as an open grant. The default view now shows actionable calls only; closed calls
remain reachable through an explicit filter rather than being erased.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
OPPS_JS = (WEB / "opportunities.js").read_text(encoding="utf-8")
INDEX = (WEB / "index.html").read_text(encoding="utf-8")


def test_default_lifecycle_view_is_actionable_not_all():
    assert "opportunityEls.filter?.value || 'actionable'" in OPPS_JS
    assert '<option value="actionable">' in INDEX
    # the actionable branch must drop both closed and date-expired calls
    assert "if (lifecycle === 'actionable')" in OPPS_JS
    assert "item.lifecycle === 'closed' || opportunityExpired(item)" in OPPS_JS


def test_a_passed_deadline_is_never_shown_as_open():
    assert "function opportunityExpired(item)" in OPPS_JS
    assert "closes < new Date()" in OPPS_JS
    # an explicit non-closed lifecycle selection also excludes expired records
    assert "if (lifecycle !== 'closed' && opportunityExpired(item)) return false;" in OPPS_JS


def test_closed_calls_remain_reachable_and_hiding_is_disclosed():
    # provenance preserved: closed is still selectable, not deleted from the feed
    assert '<option value="closed">Closed</option>' in INDEX
    assert '<option value="all">' in INDEX
    # and the default view says what it is holding back rather than implying nothing exists
    assert "closed or expired" in OPPS_JS
    assert 'id="opportunityHiddenNote"' in INDEX
