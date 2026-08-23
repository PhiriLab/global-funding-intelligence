import asyncio
import json
from datetime import datetime, timezone

import pytest

import observatory.publish_public_opportunities as publisher
from observatory.funding_models import Opportunity, OpportunityStatus
from observatory.multi_source_public_feed import SourceCollectionResult
from observatory.public_funding_export import SourceState
from observatory.public_opportunity_feed import PublicSourceHealth, SourceHealthState, build_public_feed


NOW = datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc)


def opportunity(source_id: str, external_id: str, title: str) -> Opportunity:
    return Opportunity(
        source_id=source_id,
        external_id=external_id,
        title=title,
        funder="Test Funder",
        primary_url=f"https://example.org/{source_id}/{external_id}",
        status=OpportunityStatus.open,
        closing_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        source_checked_at=NOW,
    )


def health(source_id: str, state: SourceHealthState) -> PublicSourceHealth:
    return PublicSourceHealth(
        source_id=source_id,
        source_state=SourceState.structured_beta,
        health=state,
        checked_at=NOW,
        discovered=1,
        accepted=1 if state != SourceHealthState.unavailable else 0,
    )


def test_valid_multi_source_feed_is_published_atomically(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    feed = build_public_feed(
        [
            opportunity("eu_funding_tenders", "EU-1", "EU call"),
            opportunity("ukri_funding_finder", "UKRI-1", "UKRI call"),
        ],
        generated_at=NOW,
        source_health=[
            health("eu_funding_tenders", SourceHealthState.healthy),
            health("ukri_funding_finder", SourceHealthState.healthy),
        ],
    )
    results = (
        SourceCollectionResult("eu_funding_tenders", (), 1, 1),
        SourceCollectionResult("ukri_funding_finder", (), 1, 1),
    )

    async def fake_fetch(**kwargs):
        assert kwargs["eu_page_size"] == 100
        assert kwargs["html_source_limit"] == 20
        return feed, results

    monkeypatch.setattr(publisher, "fetch_resilient_multi_source_public_feed", fake_fetch)
    count = asyncio.run(publisher.generate_public_opportunity_file(target, min_records=1, min_sources=2))

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert count == 2
    assert payload["opportunity_count"] == 2
    assert {item["source_id"] for item in payload["opportunities"]} == {"eu_funding_tenders", "ukri_funding_finder"}
    assert not (tmp_path / ".opportunities.json.tmp").exists()


def test_zero_record_refresh_fails_closed_and_preserves_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    original = '{"schema_version":1,"sentinel":"last-good"}\n'
    target.write_text(original, encoding="utf-8")
    feed = build_public_feed(
        [],
        generated_at=NOW,
        source_health=[
            health("eu_funding_tenders", SourceHealthState.empty),
            health("ukri_funding_finder", SourceHealthState.empty),
        ],
    )

    async def fake_fetch(**kwargs):
        return feed, ()

    monkeypatch.setattr(publisher, "fetch_resilient_multi_source_public_feed", fake_fetch)
    with pytest.raises(ValueError, match="refusing to publish 0 records"):
        asyncio.run(publisher.generate_public_opportunity_file(target, min_records=1, min_sources=2))

    assert target.read_text(encoding="utf-8") == original


def test_quorum_failure_preserves_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    original = "last-good\n"
    target.write_text(original, encoding="utf-8")
    feed = build_public_feed(
        [opportunity("ukri_funding_finder", "UK-1", "UKRI")],
        generated_at=NOW,
        source_health=[
            health("eu_funding_tenders", SourceHealthState.unavailable),
            health("ukri_funding_finder", SourceHealthState.healthy),
        ],
    )

    async def fake_fetch(**kwargs):
        return feed, ()

    monkeypatch.setattr(publisher, "fetch_resilient_multi_source_public_feed", fake_fetch)
    with pytest.raises(ValueError, match="publication quorum not met"):
        asyncio.run(publisher.generate_public_opportunity_file(target, min_sources=2))

    assert target.read_text(encoding="utf-8") == original
