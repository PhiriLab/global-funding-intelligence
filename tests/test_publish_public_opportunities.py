import asyncio
import json
from datetime import datetime, timezone

import pytest

import observatory.publish_public_opportunities as publisher
from observatory.funding_models import Opportunity, OpportunityStatus
from observatory.multi_source_public_feed import SourceCollectionResult
from observatory.public_opportunity_feed import build_public_feed


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


def test_valid_multi_source_feed_is_published_atomically(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    target.write_text('{"old":true}\n', encoding="utf-8")
    feed = build_public_feed(
        [
            opportunity("eu_funding_tenders", "EU-1", "EU call"),
            opportunity("ukri_funding_finder", "UKRI-1", "UKRI call"),
        ],
        generated_at=NOW,
    )
    results = (
        SourceCollectionResult("ukri_funding_finder", (), 3, 1),
        SourceCollectionResult("nihr_funding", (), 2, 0, ("one detail failed",)),
        SourceCollectionResult("wellcome_funding", (), 0, 0, ("discovery failed",)),
    )

    async def fake_fetch(**kwargs):
        assert kwargs["eu_page_size"] == 100
        assert kwargs["html_source_limit"] == 20
        return feed, results

    monkeypatch.setattr(publisher, "fetch_multi_source_public_feed", fake_fetch)
    count = asyncio.run(publisher.generate_public_opportunity_file(target, min_records=1))

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert count == 2
    assert payload["opportunity_count"] == 2
    assert {item["source_id"] for item in payload["opportunities"]} == {"eu_funding_tenders", "ukri_funding_finder"}
    assert not (tmp_path / ".opportunities.json.tmp").exists()


def test_zero_record_refresh_fails_closed_and_preserves_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    original = '{"schema_version":1,"sentinel":"last-good"}\n'
    target.write_text(original, encoding="utf-8")
    feed = build_public_feed([], generated_at=NOW)

    async def fake_fetch(**kwargs):
        return feed, ()

    monkeypatch.setattr(publisher, "fetch_multi_source_public_feed", fake_fetch)
    with pytest.raises(ValueError, match="refusing to publish 0 records"):
        asyncio.run(publisher.generate_public_opportunity_file(target, min_records=1))

    assert target.read_text(encoding="utf-8") == original


def test_upstream_exception_preserves_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    original = "last-good\n"
    target.write_text(original, encoding="utf-8")

    async def fake_fetch(**kwargs):
        raise RuntimeError("EU baseline unavailable")

    monkeypatch.setattr(publisher, "fetch_multi_source_public_feed", fake_fetch)
    with pytest.raises(RuntimeError, match="EU baseline unavailable"):
        asyncio.run(publisher.generate_public_opportunity_file(target))

    assert target.read_text(encoding="utf-8") == original
