import asyncio
from datetime import datetime, timezone

from observatory.eu_public_feed import fetch_public_eu_feed, fetch_public_eu_feed_json
from observatory.sources.eu_funding_tenders import EUFundingResult


NOW = datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc)


def records():
    return (
        {
            "identifier": "HORIZON-JU-GH-EDCTP3-2026-01-01",
            "title": "EDCTP3 topic",
            "frameworkProgrammeDescription": "Global Health EDCTP3",
            "statusDescription": "Open",
            "deadlineDate": "2026-09-15T17:00:00Z",
        },
        {
            "identifier": "HORIZON-HLTH-2026-01",
            "title": "General Horizon health topic",
            "frameworkProgrammeDescription": "Horizon Europe",
            "statusDescription": "Open",
            "deadlineDate": "2026-12-01T17:00:00Z",
        },
    )


def test_eu_pipeline_builds_full_and_edctp3_only_feeds(monkeypatch):
    async def fake_fetch_eu_open_calls(*, timeout=30.0, page_size=100):
        return EUFundingResult(raw={"fixture": True}, records=records())

    monkeypatch.setattr("observatory.eu_public_feed.fetch_eu_open_calls", fake_fetch_eu_open_calls)
    full = asyncio.run(fetch_public_eu_feed(generated_at=NOW))
    edctp = asyncio.run(fetch_public_eu_feed(edctp3_only=True, generated_at=NOW))
    assert full.opportunity_count == 2
    assert {item.source_id for item in full.opportunities} == {"edctp3", "eu_funding_tenders"}
    assert edctp.opportunity_count == 1
    assert edctp.opportunities[0].external_id == "HORIZON-JU-GH-EDCTP3-2026-01-01"
    assert edctp.opportunities[0].source_id == "edctp3"
    assert edctp.opportunities[0].funder == "Global Health EDCTP3 Joint Undertaking"
    assert edctp.opportunities[0].global_majority_access == "unclear"
    assert "call-specific applicant route remains unverified" in (edctp.opportunities[0].provenance_note or "")


def test_eu_pipeline_json_uses_same_public_contract(monkeypatch):
    async def fake_fetch_eu_open_calls(*, timeout=30.0, page_size=100):
        return EUFundingResult(raw={"fixture": True}, records=records())

    monkeypatch.setattr("observatory.eu_public_feed.fetch_eu_open_calls", fake_fetch_eu_open_calls)
    raw = asyncio.run(fetch_public_eu_feed_json(edctp3_only=True, generated_at=NOW, indent=None))
    assert '"schema_version":1' in raw
    assert '"opportunity_count":1' in raw
    assert '"source_id":"edctp3"' in raw
    assert "HORIZON-JU-GH-EDCTP3-2026-01-01" in raw
    assert "General Horizon health topic" not in raw
