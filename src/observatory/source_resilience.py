from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .public_funding_export import SourceState
from .public_opportunity_feed import PublicOpportunityFeed, PublicSourceHealth, SourceHealthState

_RESPONSIVE = {SourceHealthState.healthy, SourceHealthState.partial, SourceHealthState.empty}
_TRUSTED = {SourceState.structured_beta, SourceState.structured_beta_detail}


def responsive_structured_sources(feed: PublicOpportunityFeed) -> set[str]:
    return {
        item.source_id
        for item in feed.source_health
        if item.source_state in _TRUSTED and item.health in _RESPONSIVE and not item.using_last_known_good
    }


def reconcile_last_known_good(
    current: PublicOpportunityFeed,
    previous: PublicOpportunityFeed | None,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(hours=48),
) -> PublicOpportunityFeed:
    now = now or current.generated_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if previous is None:
        return current

    previous_health = {item.source_id: item for item in previous.source_health}
    failed = {
        item.source_id
        for item in current.source_health
        if item.source_state in _TRUSTED and item.health == SourceHealthState.unavailable
    }
    reusable: set[str] = set()
    for source_id in failed:
        old_health = previous_health.get(source_id)
        if old_health is None or old_health.source_state not in _TRUSTED:
            continue
        last_good_at = old_health.last_good_at or old_health.checked_at
        if last_good_at.tzinfo is None or now - last_good_at > max_age:
            continue
        if old_health.health not in _RESPONSIVE and not old_health.using_last_known_good:
            continue
        reusable.add(source_id)

    if not reusable:
        return current

    current_keys = {(item.source_id, item.external_id or str(item.primary_url)) for item in current.opportunities}
    opportunities = list(current.opportunities)
    for record in previous.opportunities:
        key = (record.source_id, record.external_id or str(record.primary_url))
        if record.source_id not in reusable or key in current_keys:
            continue
        warnings = list(record.warnings)
        marker = "Last-known-good record reused because current source refresh was unavailable"
        if marker not in warnings:
            warnings.append(marker)
        opportunities.append(record.model_copy(update={"warnings": warnings}))
        current_keys.add(key)

    health: list[PublicSourceHealth] = []
    for item in current.source_health:
        if item.source_id not in reusable:
            health.append(item)
            continue
        old = previous_health[item.source_id]
        last_good_at = old.last_good_at or old.checked_at
        health.append(item.model_copy(update={
            "health": SourceHealthState.partial,
            "using_last_known_good": True,
            "last_good_at": last_good_at,
            "last_error": item.last_error or "current refresh unavailable; using bounded last-known-good records",
            "accepted": sum(1 for record in opportunities if record.source_id == item.source_id),
        }))

    return current.model_copy(update={
        "opportunities": opportunities,
        "opportunity_count": len(opportunities),
        "source_health": health,
    })


def require_publication_quorum(feed: PublicOpportunityFeed, *, minimum_sources: int = 2) -> None:
    if minimum_sources < 1:
        raise ValueError("minimum_sources must be at least 1")
    responsive = responsive_structured_sources(feed)
    if len(responsive) < minimum_sources:
        raise ValueError(
            f"publication quorum not met: {len(responsive)} current structured sources responsive; "
            f"minimum is {minimum_sources}"
        )
