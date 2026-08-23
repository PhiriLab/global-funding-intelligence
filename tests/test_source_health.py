from datetime import datetime, timezone

from observatory.multi_source_public_feed import SourceCollectionResult, source_health_from_collection
from observatory.public_opportunity_feed import SourceHealthState, build_public_feed
from observatory.funding_models import Opportunity, OpportunityStatus


NOW = datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc)


def opportunity(source_id: str, title: str = "Example") -> Opportunity:
    return Opportunity(
        source_id=source_id,
        title=title,
        funder=source_id,
        primary_url="https://example.org/opportunity",
        status=OpportunityStatus.open,
        source_checked_at=NOW,
    )


def test_collection_health_states_are_deterministic():
    healthy = source_health_from_collection(SourceCollectionResult("ukri_funding_finder", (opportunity("ukri_funding_finder"),), 3, 1), checked_at=NOW)
    partial = source_health_from_collection(SourceCollectionResult("nihr_funding", (opportunity("nihr_funding"),), 3, 1, ("one detail failed",)), checked_at=NOW)
    unavailable = source_health_from_collection(SourceCollectionResult("wellcome_funding", (), 0, 0, ("403",)), checked_at=NOW)
    empty = source_health_from_collection(SourceCollectionResult("wellcome_funding", (), 0, 0), checked_at=NOW)

    assert healthy.health == SourceHealthState.healthy
    assert partial.health == SourceHealthState.partial
    assert unavailable.health == SourceHealthState.unavailable
    assert empty.health == SourceHealthState.empty
    assert partial.error_count == 1
    assert unavailable.last_error == "403"


def test_public_feed_can_publish_additive_source_health_without_schema_bump():
    health = source_health_from_collection(SourceCollectionResult("ukri_funding_finder", (opportunity("ukri_funding_finder"),), 1, 1), checked_at=NOW)
    feed = build_public_feed([opportunity("ukri_funding_finder")], generated_at=NOW, source_health=[health])

    assert feed.schema_version == 1
    assert len(feed.source_health) == 1
    assert feed.source_health[0].source_id == "ukri_funding_finder"
    assert feed.source_health[0].health == SourceHealthState.healthy
