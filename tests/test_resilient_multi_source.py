import asyncio
from datetime import datetime, timezone

import observatory.resilient_multi_source as resilient
from observatory.funding_models import Opportunity, OpportunityStatus
from observatory.multi_source_public_feed import SourceCollectionResult

NOW = datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc)


def result(source_id: str, accepted: int = 0, errors=()):
    opportunities = ()
    if accepted:
        opportunities = (
            Opportunity(
                source_id=source_id,
                external_id=f"{source_id}-1",
                title=f"{source_id} call",
                funder="Funder",
                primary_url=f"https://example.org/{source_id}/1",
                status=OpportunityStatus.open,
                closing_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                source_checked_at=NOW,
            ),
        )
    return SourceCollectionResult(source_id, opportunities, accepted, accepted, tuple(errors))


def test_eu_failure_does_not_abort_other_sources(monkeypatch):
    async def failed_eu(**kwargs):
        return result("eu_funding_tenders", errors=("EU unavailable",))

    async def good_ukri(*, limit):
        return result("ukri_funding_finder", accepted=1)

    async def empty(*, limit=20):
        return result("nihr_funding")

    async def gcc():
        return SourceCollectionResult("grand_challenges_canada", (), 0, 0)

    async def empty_eurostars(*, limit, generated_at):
        return result("eurostars")

    async def empty_women_techeu(*, generated_at):
        return result("women_techeu")

    async def empty_innosuisse(*, generated_at):
        return result("innosuisse_startup_innovation")

    async def empty_innobooster(*, generated_at):
        return result("innobooster")

    monkeypatch.setattr(resilient, "collect_eu", failed_eu)
    monkeypatch.setattr(resilient, "collect_ukri", good_ukri)
    monkeypatch.setattr(resilient, "collect_nihr", empty)
    monkeypatch.setattr(resilient, "collect_wellcome", empty)
    monkeypatch.setattr(resilient, "collect_science_for_africa", empty)
    monkeypatch.setattr(resilient, "collect_idrc", empty)
    monkeypatch.setattr(resilient, "collect_fogarty", empty)
    monkeypatch.setattr(resilient, "collect_grand_challenges_canada_watch", gcc)
    monkeypatch.setattr(resilient, "collect_eurostars", empty_eurostars)
    monkeypatch.setattr(resilient, "collect_women_techeu", empty_women_techeu)
    monkeypatch.setattr(resilient, "collect_innosuisse", empty_innosuisse)
    monkeypatch.setattr(resilient, "collect_innobooster", empty_innobooster)

    feed, results = asyncio.run(resilient.fetch_resilient_multi_source_public_feed(generated_at=NOW))
    assert feed.opportunity_count == 1
    assert feed.opportunities[0].source_id == "ukri_funding_finder"
    eu_health = next(x for x in feed.source_health if x.source_id == "eu_funding_tenders")
    assert eu_health.health.value == "unavailable"
    assert len(results) == 12
    assert {item.source_id for item in results} >= {
        "eurostars",
        "women_techeu",
        "innosuisse_startup_innovation",
        "innobooster",
    }
