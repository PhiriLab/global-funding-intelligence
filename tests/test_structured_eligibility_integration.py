import asyncio
from datetime import datetime, timezone

import observatory.multi_source_public_feed as multi
from observatory.funding_extract import ExtractedFundingRecord


NOW = datetime(2026, 8, 23, 2, 0, tzinfo=timezone.utc)


def _record(*evidence: str) -> ExtractedFundingRecord:
    return ExtractedFundingRecord(
        source_id="ukri_funding_finder",
        primary_url="https://www.ukri.org/opportunity/example",
        title="Structured UKRI example",
        funder="UK Research and Innovation",
        status="Open",
        closing_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        eligibility_evidence=evidence,
        source_hash="fixture",
    )


def test_collector_promotes_only_explicit_labelled_route_fields():
    async def discover(limit):
        return ("https://www.ukri.org/opportunity/example",)

    async def fetch_detail(url):
        return _record(
            "Eligible organisations: university, research institute",
            "Lead applicant countries: GB",
            "Partner countries: ZA, KE",
            "Consortium required: yes",
        )

    result = asyncio.run(multi._collect_html_source("ukri_funding_finder", discover, fetch_detail, limit=1))
    item = result.opportunities[0]
    assert item.applicant_types == ["university", "research institute"]
    assert item.lead_countries == ["GB"]
    assert item.partner_countries == ["ZA", "KE"]
    assert item.consortium_required is True


def test_collector_keeps_narrative_route_unknown():
    async def discover(limit):
        return ("https://www.ukri.org/opportunity/example",)

    async def fetch_detail(url):
        return _record(
            "You must be based at a UK research organisation eligible for UKRI funding.",
            "International project co-leads may be included.",
        )

    result = asyncio.run(multi._collect_html_source("ukri_funding_finder", discover, fetch_detail, limit=1))
    item = result.opportunities[0]
    assert item.applicant_types == []
    assert item.lead_countries == []
    assert item.partner_countries == []
    assert item.global_majority_access == "unclear"
