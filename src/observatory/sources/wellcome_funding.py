from __future__ import annotations

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_extract import ExtractedFundingRecord, extract_structured_funding

WELLCOME_SCHEMES_URL = "https://wellcome.org/research-funding/schemes"
WELLCOME_DEADLINES_URL = "https://wellcome.org/research-funding/guidance/prepare-to-apply/scheme-application-deadlines"


async def fetch_wellcome_index() -> FundingSnapshot:
    return await fetch_primary_html("wellcome_funding", WELLCOME_SCHEMES_URL, keywords=("scheme", "award", "fund", "research-funding"))


async def fetch_wellcome_deadlines() -> FundingSnapshot:
    return await fetch_primary_html("wellcome_deadlines", WELLCOME_DEADLINES_URL, keywords=("scheme", "deadline", "award", "fund"))


async def fetch_wellcome_opportunity(url: str) -> ExtractedFundingRecord:
    snapshot = await fetch_primary_html("wellcome_funding", url, keywords=("scheme", "award", "fund", "apply", "eligib"))
    return extract_structured_funding(snapshot)


async def discover_wellcome_opportunities(limit: int = 30) -> tuple[str, ...]:
    index = await fetch_wellcome_index()
    excluded = {WELLCOME_SCHEMES_URL.rstrip("/"), WELLCOME_DEADLINES_URL.rstrip("/")}
    candidates = tuple(url for url in index.candidate_links if url.rstrip("/") not in excluded)
    return candidates[: max(0, limit)]
