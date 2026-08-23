from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from .eu_public_feed import fetch_public_eu_feed
from .funding_extract import ExtractedFundingRecord, to_opportunity
from .funding_models import Opportunity, OpportunityStatus
from .public_funding_export import resolve_source_state
from .public_opportunity_feed import PublicOpportunityFeed, PublicSourceHealth, SourceHealthState, build_public_feed
from .source_eligibility_evidence import summarise_eligibility_evidence
from .structured_eligibility import extract_structured_eligibility
from .sources.fogarty_funding import collect_fogarty_opportunities
from .sources.global_health_funders import (
    discover_idrc_opportunities,
    discover_science_for_africa_opportunities,
    extract_funder_opportunity,
)
from .sources.nihr_funding import discover_nihr_opportunities, fetch_nihr_opportunity
from .sources.ukri_funding import discover_ukri_opportunities, fetch_ukri_opportunity
from .sources.wellcome_funding import discover_wellcome_opportunities, fetch_wellcome_opportunity


@dataclass(frozen=True)
class SourceCollectionResult:
    source_id: str
    opportunities: tuple[Opportunity, ...]
    discovered: int
    accepted: int
    errors: tuple[str, ...] = ()


def source_health_from_collection(result: SourceCollectionResult, *, checked_at: datetime) -> PublicSourceHealth:
    if checked_at.tzinfo is None:
        raise ValueError("checked_at must be timezone-aware")
    if result.accepted > 0 and not result.errors:
        health = SourceHealthState.healthy
    elif result.accepted > 0:
        health = SourceHealthState.partial
    elif result.errors:
        health = SourceHealthState.unavailable
    else:
        health = SourceHealthState.empty
    return PublicSourceHealth(
        source_id=result.source_id,
        source_state=resolve_source_state(result.source_id),
        health=health,
        checked_at=checked_at,
        discovered=result.discovered,
        accepted=result.accepted,
        error_count=len(result.errors),
        last_error=result.errors[-1] if result.errors else None,
    )


def _publishable_record(record: ExtractedFundingRecord) -> bool:
    if not record.title.strip() or record.title == "Untitled funding opportunity":
        return False
    if record.status and record.status.strip().lower() in {"closed", "archived"}:
        return False
    return any(
        value is not None
        for value in (
            record.status,
            record.opening_at,
            record.closing_at,
            record.min_award,
            record.max_award,
            record.total_fund,
            record.budget_text,
        )
    ) or record.rolling


def _attach_eligibility_evidence(record: ExtractedFundingRecord, opportunity: Opportunity) -> Opportunity:
    summary = summarise_eligibility_evidence(record.source_id, record.eligibility_evidence)
    if not summary.note:
        return opportunity
    base = opportunity.provenance_note or "Deterministic extraction from primary source."
    return opportunity.model_copy(update={"provenance_note": f"{base} {summary.note}"})


def _attach_structured_eligibility(record: ExtractedFundingRecord, opportunity: Opportunity) -> Opportunity:
    structured = extract_structured_eligibility(record.source_id, list(record.eligibility_evidence))
    updates = {
        "applicant_types": list(structured.applicant_types),
        "eligible_countries": list(structured.eligible_countries),
        "excluded_countries": list(structured.excluded_countries),
        "lead_countries": list(structured.lead_countries),
        "partner_countries": list(structured.partner_countries),
        "eligible_income_groups": list(structured.eligible_income_groups),
        "oda_only": structured.oda_only,
        "consortium_required": structured.consortium_required,
        "local_partner_required": structured.local_partner_required,
        "lead_location_rule": structured.lead_location_rule,
        "equity_or_lmic_requirement": structured.equity_or_lmic_requirement,
        "global_majority_access": structured.global_majority_access,
    }
    if not any(value not in (None, [], "unclear") for value in updates.values()):
        return opportunity
    note = opportunity.provenance_note or "Deterministic extraction from primary source."
    if structured.warnings:
        note += " Structured eligibility warnings: " + "; ".join(structured.warnings) + "."
    return opportunity.model_copy(update={**updates, "provenance_note": note})


async def _collect_html_source(
    source_id: str,
    discover: Callable[[int], Awaitable[tuple[str, ...]]],
    fetch_detail: Callable[[str], Awaitable[ExtractedFundingRecord]],
    *,
    limit: int,
    concurrency: int = 4,
) -> SourceCollectionResult:
    try:
        urls = await discover(limit)
    except Exception as exc:
        return SourceCollectionResult(source_id=source_id, opportunities=(), discovered=0, accepted=0, errors=(f"discovery failed: {type(exc).__name__}: {exc}",))

    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def fetch_one(url: str):
        async with semaphore:
            try:
                return await fetch_detail(url)
            except Exception as exc:
                return f"{url}: {type(exc).__name__}: {exc}"

    results = await asyncio.gather(*(fetch_one(url) for url in urls))
    opportunities: list[Opportunity] = []
    errors: list[str] = []
    for result in results:
        if isinstance(result, str):
            errors.append(result)
            continue
        if not _publishable_record(result):
            continue
        opportunity = to_opportunity(result)
        opportunity = _attach_eligibility_evidence(result, opportunity)
        opportunity = _attach_structured_eligibility(result, opportunity)
        if opportunity.status == OpportunityStatus.closed:
            continue
        opportunities.append(opportunity)

    return SourceCollectionResult(
        source_id=source_id,
        opportunities=tuple(opportunities),
        discovered=len(urls),
        accepted=len(opportunities),
        errors=tuple(errors[:20]),
    )


async def collect_ukri(*, limit: int = 20) -> SourceCollectionResult:
    return await _collect_html_source("ukri_funding_finder", discover_ukri_opportunities, fetch_ukri_opportunity, limit=limit)


async def collect_nihr(*, limit: int = 20) -> SourceCollectionResult:
    return await _collect_html_source("nihr_funding", discover_nihr_opportunities, fetch_nihr_opportunity, limit=limit)


async def collect_wellcome(*, limit: int = 20) -> SourceCollectionResult:
    return await _collect_html_source("wellcome_funding", discover_wellcome_opportunities, fetch_wellcome_opportunity, limit=limit)


async def collect_science_for_africa(*, limit: int = 20) -> SourceCollectionResult:
    async def fetch_detail(url: str) -> ExtractedFundingRecord:
        return await extract_funder_opportunity("science_for_africa", url)

    return await _collect_html_source(
        "science_for_africa",
        discover_science_for_africa_opportunities,
        fetch_detail,
        limit=limit,
    )


async def collect_idrc(*, limit: int = 20) -> SourceCollectionResult:
    async def fetch_detail(url: str) -> ExtractedFundingRecord:
        return await extract_funder_opportunity("idrc", url)

    return await _collect_html_source("idrc", discover_idrc_opportunities, fetch_detail, limit=limit)


async def collect_fogarty(*, limit: int = 20) -> SourceCollectionResult:
    try:
        opportunities = await collect_fogarty_opportunities(limit=limit)
    except Exception as exc:
        return SourceCollectionResult(
            source_id="fogarty",
            opportunities=(),
            discovered=0,
            accepted=0,
            errors=(f"discovery failed: {type(exc).__name__}: {exc}",),
        )
    return SourceCollectionResult(
        source_id="fogarty",
        opportunities=opportunities,
        discovered=len(opportunities),
        accepted=len(opportunities),
    )


async def fetch_multi_source_public_feed(
    *,
    generated_at: datetime | None = None,
    eu_page_size: int = 100,
    html_source_limit: int = 20,
) -> tuple[PublicOpportunityFeed, tuple[SourceCollectionResult, ...]]:
    generated_at = generated_at or datetime.now(timezone.utc)
    eu_feed = await fetch_public_eu_feed(generated_at=generated_at, page_size=eu_page_size)
    eu_opportunities = [
        Opportunity(
            source_id=item.source_id,
            external_id=item.external_id,
            title=item.title,
            funder=item.funder,
            programme=item.programme,
            primary_url=item.primary_url,
            status=item.status,
            opening_at=item.opening_at,
            closing_at=item.closing_at,
            currency=item.currency,
            min_award=item.min_award,
            max_award=item.max_award,
            total_fund=item.total_fund,
            applicant_types=item.applicant_types,
            eligible_countries=item.eligible_countries,
            excluded_countries=item.excluded_countries,
            lead_countries=item.lead_countries,
            partner_countries=item.partner_countries,
            eligible_income_groups=item.eligible_income_groups,
            oda_only=item.oda_only,
            consortium_required=item.consortium_required,
            local_partner_required=item.local_partner_required,
            lead_location_rule=item.lead_location_rule,
            equity_or_lmic_requirement=item.equity_or_lmic_requirement,
            global_majority_access=item.global_majority_access,
            source_checked_at=item.source_checked_at,
            provenance_note=item.provenance_note,
        )
        for item in eu_feed.opportunities
    ]

    ukri, nihr, wellcome, sfa, idrc, fogarty = await asyncio.gather(
        collect_ukri(limit=html_source_limit),
        collect_nihr(limit=html_source_limit),
        collect_wellcome(limit=html_source_limit),
        collect_science_for_africa(limit=html_source_limit),
        collect_idrc(limit=html_source_limit),
        collect_fogarty(limit=html_source_limit),
    )
    results = (ukri, nihr, wellcome, sfa, idrc, fogarty)
    combined: list[Opportunity] = eu_opportunities
    for result in results:
        combined.extend(result.opportunities)

    eu_result = SourceCollectionResult(
        source_id="eu_funding_tenders",
        opportunities=tuple(eu_opportunities),
        discovered=eu_feed.opportunity_count,
        accepted=eu_feed.opportunity_count,
    )
    source_health = [source_health_from_collection(eu_result, checked_at=generated_at)]
    source_health.extend(source_health_from_collection(result, checked_at=generated_at) for result in results)
    return build_public_feed(combined, generated_at=generated_at, source_health=source_health), results
