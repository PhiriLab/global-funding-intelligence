import asyncio

import observatory.sources.nihr_funding as nihr
from observatory.funding_adapter import FundingSnapshot


def snapshot(*links: str) -> FundingSnapshot:
    return FundingSnapshot(
        source_id="nihr_funding",
        source_url=nihr.NIHR_FUNDING_URL,
        final_url=nihr.NIHR_FUNDING_URL,
        status_code=200,
        text="",
        content_hash="fixture",
        candidate_links=tuple(links),
    )


def test_nihr_uses_canonical_funding_catalogue():
    assert nihr.NIHR_FUNDING_URL == "https://www.nihr.ac.uk/funding-opportunities"


def test_nihr_detail_url_filter_accepts_only_call_pages():
    assert nihr._is_nihr_opportunity_url(
        "https://www.nihr.ac.uk/funding/development-and-skills-enhancement-dse-award-cohort-10/2026410"
    )
    assert not nihr._is_nihr_opportunity_url("https://www.nihr.ac.uk/funding-opportunities")
    assert not nihr._is_nihr_opportunity_url("https://www.nihr.ac.uk/research-funding")
    assert not nihr._is_nihr_opportunity_url("https://www.nihr.ac.uk/funding")
    assert not nihr._is_nihr_opportunity_url("https://example.org/funding/example/123")


def test_discovery_rejects_navigation_and_deduplicates(monkeypatch):
    detail_a = "https://www.nihr.ac.uk/funding/example-call/2026001"
    detail_b = "https://www.nihr.ac.uk/funding/second-call/2026002"

    async def fake_index():
        return snapshot(
            "https://www.nihr.ac.uk/research-funding",
            "https://www.nihr.ac.uk/funding-opportunities",
            detail_a,
            detail_a,
            "https://www.nihr.ac.uk/funding-programmes",
            detail_b,
        )

    monkeypatch.setattr(nihr, "fetch_nihr_funding", fake_index)
    result = asyncio.run(nihr.discover_nihr_opportunities(limit=10))
    assert result == (detail_a, detail_b)


def test_discovery_respects_limit(monkeypatch):
    async def fake_index():
        return snapshot(
            "https://www.nihr.ac.uk/funding/a/2026001",
            "https://www.nihr.ac.uk/funding/b/2026002",
            "https://www.nihr.ac.uk/funding/c/2026003",
        )

    monkeypatch.setattr(nihr, "fetch_nihr_funding", fake_index)
    assert asyncio.run(nihr.discover_nihr_opportunities(limit=2)) == (
        "https://www.nihr.ac.uk/funding/a/2026001",
        "https://www.nihr.ac.uk/funding/b/2026002",
    )


def test_zero_limit_makes_no_network_call(monkeypatch):
    async def should_not_run():
        raise AssertionError("network discovery should not run")

    monkeypatch.setattr(nihr, "fetch_nihr_funding", should_not_run)
    assert asyncio.run(nihr.discover_nihr_opportunities(limit=0)) == ()
