from __future__ import annotations

import re
from urllib.parse import urlparse

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_extract import ExtractedFundingRecord, extract_structured_funding

UKRI_FUNDING_URL = "https://www.ukri.org/opportunity/"
UKRI_DISCOVERY_MAX_PAGES = 20
_UKRI_KEYWORDS = ("opportun", "fund", "grant", "fellow", "award")


def _ukri_page_url(page: int) -> str:
    if page < 1:
        raise ValueError("UKRI Funding Finder page must be >= 1")
    if page == 1:
        return UKRI_FUNDING_URL
    return f"{UKRI_FUNDING_URL}page/{page}/"


def _ukri_page_number(url: str) -> int | None:
    parsed = urlparse(url)
    match = re.fullmatch(r"/opportunity/page/(\d+)", parsed.path.rstrip("/"))
    return int(match.group(1)) if match else None


def _is_ukri_opportunity_detail(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path.rstrip("/")
    if host not in {"ukri.org", "www.ukri.org"}:
        return False
    if path in {"/opportunity", "/opportunity/feed"} or path.startswith("/opportunity/page/"):
        return False
    return bool(re.fullmatch(r"/opportunity/[^/]+", path))


def _detail_links(snapshot: FundingSnapshot) -> tuple[str, ...]:
    return tuple(url for url in snapshot.candidate_links if _is_ukri_opportunity_detail(url))


def _known_page_count(snapshot: FundingSnapshot) -> int:
    page_numbers = [number for url in snapshot.candidate_links if (number := _ukri_page_number(url)) is not None]
    return max([1, *page_numbers])


async def fetch_ukri_funding(page: int = 1) -> FundingSnapshot:
    return await fetch_primary_html("ukri_funding_finder", _ukri_page_url(page), keywords=_UKRI_KEYWORDS)


async def fetch_ukri_opportunity(url: str) -> ExtractedFundingRecord:
    snapshot = await fetch_primary_html("ukri_funding_finder", url, keywords=_UKRI_KEYWORDS)
    return extract_structured_funding(snapshot)


async def discover_ukri_opportunities(limit: int = 50, *, max_pages: int = UKRI_DISCOVERY_MAX_PAGES) -> tuple[str, ...]:
    if limit <= 0 or max_pages <= 0:
        return ()

    first = await fetch_ukri_funding(1)
    page_cap = min(max_pages, _known_page_count(first))
    found: list[str] = []
    seen: set[str] = set()

    def add(snapshot: FundingSnapshot) -> bool:
        for url in _detail_links(snapshot):
            if url in seen:
                continue
            seen.add(url)
            found.append(url)
            if len(found) >= limit:
                return True
        return False

    if add(first):
        return tuple(found[:limit])

    for page in range(2, page_cap + 1):
        snapshot = await fetch_ukri_funding(page)
        if add(snapshot):
            break

    return tuple(found[:limit])
