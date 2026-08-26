import asyncio
from datetime import datetime, timezone

import pytest

from observatory.funding_adapter import FundingSnapshot
from observatory.sources import european_innovation as ei

NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def snapshot(source_id: str, url: str, html: str):
    return FundingSnapshot(
        source_id=source_id,
        source_url=url,
        final_url=url,
        status_code=200,
        text=html,
        content_hash="direct123",
        candidate_links=(),
    )


def test_innosuisse_rolling_route_preserves_swiss_and_cofunding_constraints(monkeypatch):
    html = """
    <html><body><h1>Start-up Innovation Projects</h1>
    <p>Projects can be submitted on an ongoing basis. There are no tenders.</p>
    <p>Your start-up is based in Switzerland (i.e. the company’s headquarters is in Switzerland) and is registered in the Swiss registry of commerce.</p>
    <p>Your start-up has not been established for more than 5 years at the time of submission (up to 10 years in exceptional cases).</p>
    <p>Innosuisse covers a maximum of 70 per cent of the direct project costs. Your start-up pays at least 30 per cent of the costs itself as its own contribution.</p>
    <p>A research partner is not necessary and is not supported by Innosuisse as a direct subsidy recipient.</p>
    </body></html>
    """

    async def fake_fetch(*args, **kwargs):
        return snapshot("innosuisse_startup_innovation", ei.INNOSUISSE_STARTUP, html)

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    opportunity = asyncio.run(ei.fetch_innosuisse_startup_opportunity(now=NOW))
    assert opportunity.status.value == "rolling"
    assert opportunity.rolling is True
    assert opportunity.eligible_countries == ["CH"]
    assert opportunity.consortium_required is False
    assert opportunity.global_majority_access == "restricted"
    assert "70%" in (opportunity.provenance_note or "")
    assert "five years" in (opportunity.provenance_note or "")


def test_innosuisse_contract_change_fails_closed(monkeypatch):
    async def fake_fetch(*args, **kwargs):
        return snapshot("innosuisse_startup_innovation", ei.INNOSUISSE_STARTUP, "<h1>Changed page</h1>")

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    with pytest.raises(ValueError, match="no longer matches"):
        asyncio.run(ei.fetch_innosuisse_startup_opportunity(now=NOW))


def test_innobooster_current_pool_preserves_amount_and_danish_route(monkeypatch):
    html = """
    <html><body><h1>Innobooster</h1>
    <p>Danish small and medium-sized enterprises, including entrepreneurial companies.</p>
    <p>You can apply for between 200,000 DKK and 5 million DKK.</p>
    <p>Innovation Fund Denmark can co-invest a maximum of 35% of the company's relevant expenses for the project.</p>
    <p>Innobooster, 4th pool 2026 | Innobooster | 15 October 2026, at 12:00 noon</p>
    <p>Opening period | 20. August 2026 - 15. October</p>
    </body></html>
    """

    async def fake_fetch(*args, **kwargs):
        return snapshot("innobooster", ei.INNOBOOSTER, html)

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    opportunity = asyncio.run(ei.fetch_innobooster_opportunity(now=NOW))
    assert opportunity.status.value == "open"
    assert opportunity.currency == "DKK"
    assert opportunity.min_award == 200_000
    assert opportunity.max_award == 5_000_000
    assert opportunity.eligible_countries == ["DK"]
    assert opportunity.global_majority_access == "restricted"
    assert opportunity.closing_at == datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
    assert "35%" in (opportunity.provenance_note or "")


def test_innobooster_contract_change_fails_closed(monkeypatch):
    async def fake_fetch(*args, **kwargs):
        return snapshot("innobooster", ei.INNOBOOSTER, "<h1>Innobooster</h1><p>Changed terms</p>")

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    with pytest.raises(ValueError, match="no longer matches"):
        asyncio.run(ei.fetch_innobooster_opportunity(now=NOW))
