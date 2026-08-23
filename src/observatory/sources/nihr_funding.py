from __future__ import annotations

from urllib.parse import urlparse

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_extract import ExtractedFundingRecord, extract_structured_funding

NIHR_FUNDING_URL = "https://www.nihr.ac.uk/funding-opportunities"


def _is_nihr_opportunity_url(url: str) -> bool:
    """Accept only canonical NIHR call-detail pages, not programme/navigation pages."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path.rstrip("/")
    if host not in {"nihr.ac.uk", "www.nihr.ac.uk"}:
        return False
    if path in {"/funding-opportunities", "/research-funding", "/funding"}:
        return False
    # Current NIHR opportunity detail pages use /funding/<slug>/<reference>.
    parts = [part for part in path.split("/") if part]
    return len(parts) >= 3 and parts[0] == "funding"


async def fetch_nihr_funding() -> FundingSnapshot:
    return await fetch_primary_html(
        "nihr_funding",
        NIHR_FUNDING_URL,
        keywords=("fund", "call", "programme", "award", "global-health"),
    )


async def fetch_nihr_opportunity(url: str) -> ExtractedFundingRecord:
    if not _is_nihr_opportunity_url(url):
        raise ValueError("NIHR detail URL is not a canonical funding opportunity page")
    snapshot = await fetch_primary_html(
        "nihr_funding",
        url,
        keywords=("fund", "call", "programme", "award", "global-health"),
    )
    return extract_structured_funding(snapshot)


async def discover_nihr_opportunities(limit: int = 50) -> tuple[str, ...]:
    if limit <= 0:
        return ()
    index = await fetch_nihr_funding()
    found: list[str] = []
    seen: set[str] = set()
    for url in index.candidate_links:
        if url in seen or not _is_nihr_opportunity_url(url):
            continue
        seen.add(url)
        found.append(url)
        if len(found) >= limit:
            break
    return tuple(found)
