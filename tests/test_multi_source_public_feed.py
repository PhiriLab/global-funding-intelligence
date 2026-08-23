import asyncio
from datetime import datetime, timezone

import observatory.multi_source_public_feed as multi
from observatory.funding_extract import ExtractedFundingRecord
from observatory.funding_models import Opportunity, OpportunityStatus
from observatory.multi_source_public_feed import SourceCollectionResult
from observatory.public_opportunity_feed import build_public_feed


NOW = datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc)


def extracted(source_id: str, url: str, title: str, *, status: str = "Open", eligibility_evidence=()) -> ExtractedFundingRecord:
    return ExtractedFundingRecord(
        source_id=source_id,
        primary_url=url,
        title=title,
        funder=source_id,
        status=status,
        closing_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        eligibility_evidence=eligibility_evidence,
        source_hash="fixture",
    )


def test_html_collector_isolates_detail_failures_and_accepts_structured_calls():
    async def discover(limit):
        assert limit == 3
        return ("https://example.org/a", "https://example.org/b", "https://example.org/c")

    async def fetch_detail(url):
        if url.endswith("/b"):
            raise RuntimeError("blocked")
        if url.endswith("/c"):
            return ExtractedFundingRecord(source_id="ukri_funding_finder", primary_url=url, title="Generic page")
        return extracted("ukri_funding_finder", url, "Live UKRI call")

    result = asyncio.run(multi._collect_html_source("ukri_funding_finder", discover, fetch_detail, limit=3, concurrency=2))
    assert result.discovered == 3
    assert result.accepted == 1
    assert len(result.opportunities) == 1
    assert result.opportunities[0].title == "Live UKRI call"
    assert len(result.errors) == 1 and "blocked" in result.errors[0]


def test_html_collector_preserves_source_eligibility_evidence_without_route_inference():
    async def discover(limit):
        return ("https://www.ukri.org/opportunity/example",)

    async def fetch_detail(url):
        return extracted(
            "ukri_funding_finder",
            url,
            "UKRI example",
            eligibility_evidence=(
                "You must be based at a UK research organisation eligible for UKRI funding.",
                "International project co-leads may be included.",
            ),
        )

    result = asyncio.run(multi._collect_html_source("ukri_funding_finder", discover, fetch_detail, limit=1))
    opportunity = result.opportunities[0]
    assert "UK research-organisation requirement stated" in opportunity.provenance_note
    assert "international participation wording stated" in opportunity.provenance_note
    assert opportunity.eligible_countries == []
    assert opportunity.lead_countries == []
    assert opportunity.partner_countries == []
    assert opportunity.global_majority_access == "unclear"


def test_html_collector_rejects_closed_records():
    async def discover(limit):
        return ("https://example.org/closed",)

    async def fetch_detail(url):
        return extracted("nihr_funding", url, "Closed NIHR call", status="Closed")

    result = asyncio.run(multi._collect_html_source("nihr_funding", discover, fetch_detail, limit=2))
    assert result.accepted == 0
    assert result.opportunities == ()


def test_multi_source_feed_keeps_eu_when_optional_sources_fail(monkeypatch):
    eu = Opportunity(
        source_id="eu_funding_tenders",
        external_id="EU-1",
        title="EU baseline",
        funder="European Commission",
        primary_url="https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/EU-1",
        status=OpportunityStatus.open,
        closing_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        source_checked_at=NOW,
    )
    eu_feed = build_public_feed([eu], generated_at=NOW)

    async def fake_eu(**kwargs):
        return eu_feed

    async def good_ukri(*, limit):
        ukri = Opportunity(
            source_id="ukri_funding_finder",
            title="UKRI call",
            funder="UK Research and Innovation",
            primary_url="https://www.ukri.org/opportunity/example",
            status=OpportunityStatus.open,
            closing_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
            source_checked_at=NOW,
        )
        return SourceCollectionResult("ukri_funding_finder", (ukri,), 1, 1)

    async def failed_nihr(*, limit):
        return SourceCollectionResult("nihr_funding", (), 0, 0, ("discovery failed",))

    async def failed_wellcome(*, limit):
        return SourceCollectionResult("wellcome_funding", (), 0, 0, ("403",))

    async def empty_sfa(*, limit):
        return SourceCollectionResult("science_for_africa", (), 0, 0)

    async def empty_idrc(*, limit):
        return SourceCollectionResult("idrc", (), 0, 0)

    async def empty_fogarty(*, limit):
        return SourceCollectionResult("fogarty", (), 0, 0)

    monkeypatch.setattr(multi, "fetch_public_eu_feed", fake_eu)
    monkeypatch.setattr(multi, "collect_ukri", good_ukri)
    monkeypatch.setattr(multi, "collect_nihr", failed_nihr)
    monkeypatch.setattr(multi, "collect_wellcome", failed_wellcome)
    monkeypatch.setattr(multi, "collect_science_for_africa", empty_sfa)
    monkeypatch.setattr(multi, "collect_idrc", empty_idrc)
    monkeypatch.setattr(multi, "collect_fogarty", empty_fogarty)

    feed, results = asyncio.run(multi.fetch_multi_source_public_feed(generated_at=NOW, html_source_limit=5))
    assert feed.opportunity_count == 2
    assert {item.source_id for item in feed.opportunities} == {"eu_funding_tenders", "ukri_funding_finder"}
    assert len(results) == 6
    assert results[1].errors == ("discovery failed",)
    assert results[2].errors == ("403",)
    assert results[3].source_id == "science_for_africa"
    assert results[4].source_id == "idrc"
    assert results[5].source_id == "fogarty"
