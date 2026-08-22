from __future__ import annotations

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_extract import ExtractedFundingRecord, extract_structured_funding

UKRI_FUNDING_URL = "https://www.ukri.org/opportunity/"


async def fetch_ukri_funding() -> FundingSnapshot:
    return await fetch_primary_html("ukri_funding_finder", UKRI_FUNDING_URL, keywords=("opportun", "fund", "grant", "fellow", "award"))


async def fetch_ukri_opportunity(url: str) -> ExtractedFundingRecord:
    snapshot = await fetch_primary_html("ukri_funding_finder", url, keywords=("opportun", "fund", "grant", "fellow", "award"))
    return extract_structured_funding(snapshot)


async def discover_ukri_opportunities(limit: int = 50) -> tuple[str, ...]:
    index = await fetch_ukri_funding()
    return index.candidate_links[:limit]
