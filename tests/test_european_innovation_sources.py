import asyncio
from datetime import datetime, timezone

from observatory.funding_adapter import FundingSnapshot
from observatory.sources import european_innovation as ei

NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def snapshot(source_id: str, url: str, html: str, links=()):
    return FundingSnapshot(
        source_id=source_id,
        source_url=url,
        final_url=url,
        status_code=200,
        text=html,
        content_hash="abc123",
        candidate_links=tuple(links),
    )


def test_eurostars_detail_filter_is_narrow():
    assert ei._is_eurostars_call_url(
        "https://www.eurekanetwork.org/programmes-and-calls/eurostars/eurostars-call-for-projects-september-2026/"
    )
    assert not ei._is_eurostars_call_url(
        "https://www.eurekanetwork.org/programmes-and-calls/eurostars/eurostars-resource-library/"
    )


def test_discover_eurostars_calls_excludes_resources(monkeypatch):
    index = snapshot(
        "eurostars",
        ei.EUROSTARS_INDEX,
        "<html></html>",
        links=(
            "https://www.eurekanetwork.org/programmes-and-calls/eurostars/eurostars-resource-library/",
            "https://www.eurekanetwork.org/programmes-and-calls/eurostars/eurostars-call-for-projects-september-2026/",
        ),
    )

    async def fake_fetch(*args, **kwargs):
        return index

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    result = asyncio.run(ei.discover_eurostars_calls())
    assert len(result) == 1
    assert result[0].endswith("eurostars-call-for-projects-september-2026")


def test_eurostars_call_preserves_national_funding_caveat(monkeypatch):
    html = """
    <html><body><h1>Eurostars Call 11 for projects – deadline September 2026</h1>
    <p>Start Date:</p><p>9 July 2026, 12:00 AM CEST</p>
    <p>End Date:</p><p>10 September 2026, 2:00 PM CEST</p>
    <h2>Countries and regions</h2><p>South Africa</p><p>United Kingdom</p>
    <p>Your project consortium must have an innovative SME in the leading role, but it can also include large companies, universities, research organisations and more.</p>
    <p>Funding rules vary from country to country and your National Funding Body decides which organisations receive funding and funding rates.</p>
    </body></html>
    """
    detail_url = "https://www.eurekanetwork.org/programmes-and-calls/eurostars/eurostars-call-for-projects-september-2026/"

    async def fake_fetch(*args, **kwargs):
        return snapshot("eurostars", detail_url, html)

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    opportunity = asyncio.run(ei.fetch_eurostars_call(detail_url, now=NOW))
    assert opportunity.status.value == "open"
    assert opportunity.closing_at == datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    assert opportunity.global_majority_access == "direct"
    assert opportunity.consortium_required is True
    assert "national/regional funding bodies" in (opportunity.provenance_note or "")
    assert "innovative SME" in opportunity.applicant_types


def test_women_techeu_two_stage_grant_is_not_flattened(monkeypatch):
    html = """
    <html><body>
    <h1>Active Calls</h1>
    <p>CALL IS OPEN.</p>
    <p>Women TechEU 2 EIC is an EU-funded project designed to support women-led early-stage deep tech startups from Europe.</p>
    <p>Selected startups will receive €75,000 in non-dilutive funding.</p>
    <p>The new call follows a two-stage application process.</p>
    <p>Women TechEU 2 EIC – Eligibility Strand</p>
    <p>Opening date: 1 June 2026</p>
    <p>Final cut-off: 14 June 2027 at 17:00 CEST</p>
    <p>Women TechEU 2 EIC – Full Proposal Strand</p>
    <p>Submission deadline 5: 16 September 2026 at 17:00 CEST</p>
    <p>Submission deadline 6: 14 January 2027 at 17:00 CET</p>
    <p>Submission deadline 7: 1 April 2027 at 17:00 CEST</p>
    <p>Submission deadline 8: 8 July 2027 at 17:00 CEST</p>
    </body></html>
    """

    async def fake_fetch(*args, **kwargs):
        return snapshot("women_techeu", ei.WOMEN_TECHEU_ACTIVE, html)

    monkeypatch.setattr(ei, "fetch_primary_html", fake_fetch)
    opportunity = asyncio.run(ei.fetch_women_techeu_opportunity(now=NOW))
    assert opportunity.status.value == "rolling"
    assert opportunity.currency == "EUR"
    assert opportunity.max_award == 75000
    assert opportunity.global_majority_access == "restricted"
    assert opportunity.consortium_required is False
    assert opportunity.closing_at == datetime(2027, 6, 14, 15, 0, tzinfo=timezone.utc)
    assert "two-stage process" in (opportunity.provenance_note or "")
    assert "16 September 2026" in (opportunity.provenance_note or "")
