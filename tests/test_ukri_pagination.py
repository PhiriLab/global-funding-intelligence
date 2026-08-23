import asyncio

import observatory.sources.ukri_funding as ukri
from observatory.funding_adapter import FundingSnapshot


def snapshot(page: int, links: tuple[str, ...]) -> FundingSnapshot:
    url = ukri._ukri_page_url(page)
    return FundingSnapshot(
        source_id="ukri_funding_finder",
        source_url=url,
        final_url=url,
        status_code=200,
        text="fixture",
        content_hash=f"page-{page}",
        candidate_links=links,
    )


def test_ukri_detail_filter_excludes_index_and_pagination_urls():
    assert ukri._is_ukri_opportunity_detail("https://www.ukri.org/opportunity/bbsrc-proof-of-concept-2026")
    assert not ukri._is_ukri_opportunity_detail("https://www.ukri.org/opportunity/")
    assert not ukri._is_ukri_opportunity_detail("https://www.ukri.org/opportunity/page/2/")
    assert not ukri._is_ukri_opportunity_detail("https://example.org/opportunity/not-ukri")


def test_known_page_count_uses_funding_finder_pagination_links():
    item = snapshot(1, (
        "https://www.ukri.org/opportunity/call-one",
        "https://www.ukri.org/opportunity/page/2",
        "https://www.ukri.org/opportunity/page/13",
    ))
    assert ukri._known_page_count(item) == 13


def test_discovery_collects_multiple_pages_deduplicates_and_stops_at_limit(monkeypatch):
    pages = {
        1: snapshot(1, (
            "https://www.ukri.org/opportunity/call-a",
            "https://www.ukri.org/opportunity/call-b",
            "https://www.ukri.org/opportunity/page/2",
            "https://www.ukri.org/opportunity/page/3",
        )),
        2: snapshot(2, (
            "https://www.ukri.org/opportunity/call-b",
            "https://www.ukri.org/opportunity/call-c",
            "https://www.ukri.org/opportunity/page/3",
        )),
        3: snapshot(3, ("https://www.ukri.org/opportunity/call-d",)),
    }
    requested = []

    async def fake_fetch(page=1):
        requested.append(page)
        return pages[page]

    monkeypatch.setattr(ukri, "fetch_ukri_funding", fake_fetch)
    result = asyncio.run(ukri.discover_ukri_opportunities(limit=3))
    assert result == (
        "https://www.ukri.org/opportunity/call-a",
        "https://www.ukri.org/opportunity/call-b",
        "https://www.ukri.org/opportunity/call-c",
    )
    assert requested == [1, 2]


def test_discovery_respects_hard_page_cap(monkeypatch):
    first = snapshot(1, (
        "https://www.ukri.org/opportunity/call-a",
        "https://www.ukri.org/opportunity/page/9",
    ))
    second = snapshot(2, ("https://www.ukri.org/opportunity/call-b",))
    requested = []

    async def fake_fetch(page=1):
        requested.append(page)
        return first if page == 1 else second

    monkeypatch.setattr(ukri, "fetch_ukri_funding", fake_fetch)
    result = asyncio.run(ukri.discover_ukri_opportunities(limit=20, max_pages=2))
    assert result == (
        "https://www.ukri.org/opportunity/call-a",
        "https://www.ukri.org/opportunity/call-b",
    )
    assert requested == [1, 2]


def test_zero_limit_performs_no_network_work(monkeypatch):
    async def fail_fetch(page=1):
        raise AssertionError("network should not be called")

    monkeypatch.setattr(ukri, "fetch_ukri_funding", fail_fetch)
    assert asyncio.run(ukri.discover_ukri_opportunities(limit=0)) == ()
