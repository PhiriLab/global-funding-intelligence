from datetime import datetime, timedelta, timezone

import pytest

from observatory.funding_models import Opportunity, OpportunityStatus
from observatory.public_funding_export import SourceState
from observatory.public_opportunity_feed import PublicSourceHealth, SourceHealthState, build_public_feed
from observatory.source_resilience import reconcile_last_known_good, require_publication_quorum

NOW = datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc)


def opp(source_id: str, external_id: str) -> Opportunity:
    return Opportunity(
        source_id=source_id,
        external_id=external_id,
        title=f"{source_id} call",
        funder="Funder",
        primary_url=f"https://example.org/{source_id}/{external_id}",
        status=OpportunityStatus.open,
        closing_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        source_checked_at=NOW - timedelta(hours=2),
    )


def health(source_id: str, state: SourceHealthState, *, checked_at=NOW, lkg=False):
    return PublicSourceHealth(
        source_id=source_id,
        source_state=SourceState.structured_beta,
        health=state,
        checked_at=checked_at,
        discovered=1,
        accepted=1 if state != SourceHealthState.unavailable else 0,
        using_last_known_good=lkg,
    )


def test_failed_source_reuses_only_its_own_bounded_lkg_records():
    previous = build_public_feed(
        [opp("eu_funding_tenders", "EU-1"), opp("ukri_funding_finder", "UK-1")],
        generated_at=NOW - timedelta(hours=2),
        source_health=[
            health("eu_funding_tenders", SourceHealthState.healthy, checked_at=NOW - timedelta(hours=2)),
            health("ukri_funding_finder", SourceHealthState.healthy, checked_at=NOW - timedelta(hours=2)),
        ],
    )
    current = build_public_feed(
        [opp("ukri_funding_finder", "UK-2")],
        generated_at=NOW,
        source_health=[
            health("eu_funding_tenders", SourceHealthState.unavailable),
            health("ukri_funding_finder", SourceHealthState.healthy),
        ],
    )
    merged = reconcile_last_known_good(current, previous, now=NOW)
    assert {(x.source_id, x.external_id) for x in merged.opportunities} == {
        ("eu_funding_tenders", "EU-1"),
        ("ukri_funding_finder", "UK-2"),
    }
    eu = next(x for x in merged.source_health if x.source_id == "eu_funding_tenders")
    assert eu.using_last_known_good is True
    assert eu.health == SourceHealthState.partial
    assert eu.last_good_at == NOW - timedelta(hours=2)


def test_stale_lkg_is_not_reused():
    previous = build_public_feed(
        [opp("eu_funding_tenders", "EU-1")],
        generated_at=NOW - timedelta(hours=72),
        source_health=[health("eu_funding_tenders", SourceHealthState.healthy, checked_at=NOW - timedelta(hours=72))],
    )
    current = build_public_feed(
        [],
        generated_at=NOW,
        source_health=[health("eu_funding_tenders", SourceHealthState.unavailable)],
    )
    merged = reconcile_last_known_good(current, previous, now=NOW, max_age=timedelta(hours=48))
    assert merged.opportunities == []
    assert merged.source_health[0].using_last_known_good is False


def test_lkg_does_not_count_toward_current_publication_quorum():
    feed = build_public_feed(
        [opp("ukri_funding_finder", "UK-1")],
        generated_at=NOW,
        source_health=[
            health("ukri_funding_finder", SourceHealthState.healthy),
            PublicSourceHealth(
                source_id="eu_funding_tenders",
                source_state=SourceState.structured_beta,
                health=SourceHealthState.partial,
                checked_at=NOW,
                using_last_known_good=True,
                last_good_at=NOW - timedelta(hours=2),
            ),
        ],
    )
    with pytest.raises(ValueError, match="publication quorum not met"):
        require_publication_quorum(feed, minimum_sources=2)
    require_publication_quorum(feed, minimum_sources=1)
