import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import observatory.publish_public_opportunities as publisher


NOW = datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc)


def feed_json(count: int) -> str:
    opportunities = []
    for index in range(count):
        opportunities.append(
            {
                "source_id": "eu_funding_tenders",
                "external_id": f"EDCTP3-{index}",
                "title": f"Call {index}",
                "funder": "European Commission",
                "primary_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/EDCTP3-{index}",
                "source_state": "structured_beta",
                "source_checked_at": NOW.isoformat(),
                "status": "open",
                "lifecycle": "open",
                "global_majority_access": "unclear",
                "eligibility": "Not determined — verify at source",
                "warnings": [],
            }
        )
    return json.dumps(
        {
            "schema_version": 1,
            "generated_at": NOW.isoformat(),
            "opportunity_count": count,
            "opportunities": opportunities,
        }
    )


def test_valid_feed_is_published_atomically(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    target.write_text('{"old":true}\n', encoding="utf-8")

    async def fake_fetch(**kwargs):
        assert kwargs["page_size"] == 100
        return feed_json(2)

    monkeypatch.setattr(publisher, "fetch_public_eu_feed_json", fake_fetch)
    count = asyncio.run(publisher.generate_public_opportunity_file(target, min_records=1))

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert count == 2
    assert payload["opportunity_count"] == 2
    assert not (tmp_path / ".opportunities.json.tmp").exists()


def test_zero_record_refresh_fails_closed_and_preserves_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    original = '{"schema_version":1,"sentinel":"last-good"}\n'
    target.write_text(original, encoding="utf-8")

    async def fake_fetch(**kwargs):
        return feed_json(0)

    monkeypatch.setattr(publisher, "fetch_public_eu_feed_json", fake_fetch)
    with pytest.raises(ValueError, match="refusing to publish 0 records"):
        asyncio.run(publisher.generate_public_opportunity_file(target, min_records=1))

    assert target.read_text(encoding="utf-8") == original


def test_malformed_feed_fails_before_destination_is_modified(tmp_path, monkeypatch):
    target = tmp_path / "opportunities.json"
    original = "last-good\n"
    target.write_text(original, encoding="utf-8")

    async def fake_fetch(**kwargs):
        return "not-json"

    monkeypatch.setattr(publisher, "fetch_public_eu_feed_json", fake_fetch)
    with pytest.raises(ValueError, match="not valid JSON"):
        asyncio.run(publisher.generate_public_opportunity_file(target))

    assert target.read_text(encoding="utf-8") == original
