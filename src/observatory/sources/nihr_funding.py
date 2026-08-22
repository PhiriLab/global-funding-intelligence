from __future__ import annotations

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_extract import ExtractedFundingRecord, extract_structured_funding

NIHR_FUNDING_URL = "https://www.nihr.ac.uk/research-funding"


async def fetch_nihr_funding() -> FundingSnapshot:
    return await fetch_primary_html("nihr_funding", NIHR_FUNDING_URL, keywords=("fund", "call", "programme", "award", "global-health"))


async def fetch_nihr_opportunity(url: str) -> ExtractedFundingRecord:
    snapshot = await fetch_primary_html("nihr_funding", url, keywords=("fund", "call", "programme", "award", "global-health"))
    return extract_structured_funding(snapshot)


async def discover_nihr_opportunities(limit: int = 50) -> tuple[str, ...]:
    index = await fetch_nihr_funding()
    return index.candidate_links[:limit]
