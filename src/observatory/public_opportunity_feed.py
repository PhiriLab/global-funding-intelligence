from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl

from .funding_models import Opportunity, OpportunityStatus
from .public_funding_export import SourceState, resolve_source_state


class OpportunityLifecycle(str, Enum):
    open = "open"
    closing_soon = "closing_soon"
    upcoming = "upcoming"
    rolling = "rolling"
    closed = "closed"
    unknown = "unknown"


class SourceHealthState(str, Enum):
    healthy = "healthy"
    partial = "partial"
    unavailable = "unavailable"
    empty = "empty"


class PublicSourceHealth(BaseModel):
    source_id: str
    source_state: SourceState
    health: SourceHealthState
    checked_at: datetime
    discovered: int = 0
    accepted: int = 0
    error_count: int = 0
    last_error: str | None = None


class PublicOpportunityRecord(BaseModel):
    source_id: str
    external_id: str | None = None
    title: str
    funder: str
    programme: str | None = None
    primary_url: HttpUrl
    source_state: SourceState
    source_checked_at: datetime
    status: OpportunityStatus
    lifecycle: OpportunityLifecycle
    opening_at: datetime | None = None
    closing_at: datetime | None = None
    currency: str | None = None
    min_award: float | None = None
    max_award: float | None = None
    total_fund: float | None = None

    # Applicant-route fields are copied only from trusted structured Opportunity
    # fields. Empty collections / null values mean "not deterministically verified".
    applicant_types: list[str] = Field(default_factory=list)
    eligible_countries: list[str] = Field(default_factory=list)
    excluded_countries: list[str] = Field(default_factory=list)
    lead_countries: list[str] = Field(default_factory=list)
    partner_countries: list[str] = Field(default_factory=list)
    eligible_income_groups: list[str] = Field(default_factory=list)
    oda_only: bool | None = None
    consortium_required: bool | None = None
    local_partner_required: bool | None = None
    lead_location_rule: str | None = None
    equity_or_lmic_requirement: str | None = None
    global_majority_access: str = "unclear"

    eligibility: str = "Not determined — verify at source"
    provenance_note: str | None = None
    warnings: list[str] = Field(default_factory=list)


class PublicOpportunityFeed(BaseModel):
    schema_version: int = 1
    generated_at: datetime
    opportunity_count: int
    opportunities: list[PublicOpportunityRecord]
    source_health: list[PublicSourceHealth] = Field(default_factory=list)


def classify_lifecycle(opportunity: Opportunity, *, now: datetime | None = None, closing_soon_days: int = 30) -> OpportunityLifecycle:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if opportunity.rolling or opportunity.status == OpportunityStatus.rolling:
        return OpportunityLifecycle.rolling
    if opportunity.status == OpportunityStatus.closed:
        return OpportunityLifecycle.closed
    if opportunity.closing_at is not None and opportunity.closing_at < now:
        return OpportunityLifecycle.closed
    if opportunity.opening_at is not None and opportunity.opening_at > now:
        return OpportunityLifecycle.upcoming
    if opportunity.status in {OpportunityStatus.upcoming, OpportunityStatus.forecast}:
        return OpportunityLifecycle.upcoming
    if opportunity.status == OpportunityStatus.open:
        if opportunity.closing_at is not None:
            remaining = opportunity.closing_at - now
            if remaining.total_seconds() >= 0 and remaining.days < closing_soon_days:
                return OpportunityLifecycle.closing_soon
        return OpportunityLifecycle.open
    return OpportunityLifecycle.unknown


def _has_applicant_route_evidence(opportunity: Opportunity) -> bool:
    return bool(
        opportunity.applicant_types
        or opportunity.eligible_countries
        or opportunity.excluded_countries
        or opportunity.lead_countries
        or opportunity.partner_countries
        or opportunity.eligible_income_groups
        or opportunity.oda_only is not None
        or opportunity.consortium_required is not None
        or opportunity.local_partner_required is not None
        or opportunity.lead_location_rule
        or opportunity.equity_or_lmic_requirement
        or opportunity.global_majority_access != "unclear"
    )


def to_public_opportunity(opportunity: Opportunity, *, now: datetime | None = None) -> PublicOpportunityRecord:
    source_state = resolve_source_state(opportunity.source_id)
    if source_state not in {SourceState.structured_beta, SourceState.structured_beta_detail}:
        raise ValueError(
            f"source {opportunity.source_id!r} is {source_state.value!r}; "
            "only trusted structured sources may publish opportunity-level fields"
        )
    warnings: list[str] = []
    if opportunity.closing_at is None and not opportunity.rolling:
        warnings.append("No verified closing date in structured source data")
    if opportunity.global_majority_access == "unclear":
        warnings.append("Global Majority participation route is not yet deterministically verified")
    if not _has_applicant_route_evidence(opportunity):
        warnings.append("Applicant country and organisation routes are not yet deterministically verified")
    return PublicOpportunityRecord(
        source_id=opportunity.source_id,
        external_id=opportunity.external_id,
        title=opportunity.title,
        funder=opportunity.funder,
        programme=opportunity.programme,
        primary_url=opportunity.primary_url,
        source_state=source_state,
        source_checked_at=opportunity.source_checked_at,
        status=opportunity.status,
        lifecycle=classify_lifecycle(opportunity, now=now),
        opening_at=opportunity.opening_at,
        closing_at=opportunity.closing_at,
        currency=opportunity.currency,
        min_award=opportunity.min_award,
        max_award=opportunity.max_award,
        total_fund=opportunity.total_fund,
        applicant_types=opportunity.applicant_types,
        eligible_countries=opportunity.eligible_countries,
        excluded_countries=opportunity.excluded_countries,
        lead_countries=opportunity.lead_countries,
        partner_countries=opportunity.partner_countries,
        eligible_income_groups=opportunity.eligible_income_groups,
        oda_only=opportunity.oda_only,
        consortium_required=opportunity.consortium_required,
        local_partner_required=opportunity.local_partner_required,
        lead_location_rule=opportunity.lead_location_rule,
        equity_or_lmic_requirement=opportunity.equity_or_lmic_requirement,
        global_majority_access=opportunity.global_majority_access,
        provenance_note=opportunity.provenance_note,
        warnings=warnings,
    )


def _record_identity(record: PublicOpportunityRecord) -> tuple[str, str]:
    return record.source_id, record.external_id or str(record.primary_url)


def build_public_feed(
    opportunities: list[Opportunity] | tuple[Opportunity, ...],
    *,
    generated_at: datetime | None = None,
    source_health: list[PublicSourceHealth] | tuple[PublicSourceHealth, ...] = (),
) -> PublicOpportunityFeed:
    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        raise ValueError("generated_at must be timezone-aware")
    deduped: dict[tuple[str, str], PublicOpportunityRecord] = {}
    for opportunity in opportunities:
        record = to_public_opportunity(opportunity, now=generated_at)
        key = _record_identity(record)
        existing = deduped.get(key)
        if existing is None or record.source_checked_at > existing.source_checked_at:
            deduped[key] = record
    lifecycle_rank = {
        OpportunityLifecycle.closing_soon: 0,
        OpportunityLifecycle.open: 1,
        OpportunityLifecycle.rolling: 2,
        OpportunityLifecycle.upcoming: 3,
        OpportunityLifecycle.unknown: 4,
        OpportunityLifecycle.closed: 5,
    }
    sentinel = datetime.max.replace(tzinfo=timezone.utc)
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            lifecycle_rank[item.lifecycle],
            item.closing_at or sentinel,
            item.funder.casefold(),
            item.title.casefold(),
            item.source_id,
            item.external_id or str(item.primary_url),
        ),
    )
    ordered_health = sorted(source_health, key=lambda item: item.source_id)
    return PublicOpportunityFeed(
        generated_at=generated_at,
        opportunity_count=len(ordered),
        opportunities=ordered,
        source_health=list(ordered_health),
    )


def public_feed_json(
    opportunities: list[Opportunity] | tuple[Opportunity, ...],
    *,
    generated_at: datetime | None = None,
    source_health: list[PublicSourceHealth] | tuple[PublicSourceHealth, ...] = (),
    indent: int | None = 2,
) -> str:
    feed = build_public_feed(opportunities, generated_at=generated_at, source_health=source_health)
    return feed.model_dump_json(indent=indent, exclude_none=True)
