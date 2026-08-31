from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .eu_public_feed import fetch_public_eu_feed
from .funding_models import Opportunity
from .multi_source_public_feed import (
    SourceCollectionResult,
    collect_fogarty,
    collect_grand_challenges_canada_watch,
    collect_idrc,
    collect_nihr,
    collect_science_for_africa,
    collect_ukri,
    collect_wellcome,
    source_health_from_collection,
)
from .public_opportunity_feed import PublicOpportunityFeed, build_public_feed
from .sources.european_innovation import (
    collect_eurostars_opportunities,
    collect_innobooster_opportunities,
    collect_innosuisse_startup_opportunities,
    collect_women_techeu_opportunities,
)


def _opportunity_from_public(item) -> Opportunity:
    return Opportunity(
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


async def collect_eu(*, generated_at: datetime, page_size: int = 100) -> SourceCollectionResult:
    try:
        feed = await fetch_public_eu_feed(generated_at=generated_at, page_size=page_size)
    except Exception as exc:
        return SourceCollectionResult(
            "eu_funding_tenders",
            (),
            0,
            0,
            (f"discovery failed: {type(exc).__name__}: {exc}",),
        )
    opportunities = tuple(_opportunity_from_public(item) for item in feed.opportunities)
    return SourceCollectionResult(
        "eu_funding_tenders",
        opportunities,
        feed.opportunity_count,
        feed.opportunity_count,
    )


async def _collect_innovation(source_id: str, loader) -> SourceCollectionResult:
    try:
        opportunities = await loader()
    except Exception as exc:
        return SourceCollectionResult(
            source_id,
            (),
            0,
            0,
            (f"discovery failed: {type(exc).__name__}: {exc}",),
        )
    return SourceCollectionResult(
        source_id,
        opportunities,
        len(opportunities),
        len(opportunities),
    )


async def collect_eurostars(*, limit: int = 5, generated_at: datetime) -> SourceCollectionResult:
    async def loader():
        return await collect_eurostars_opportunities(limit=limit, now=generated_at)
    return await _collect_innovation("eurostars", loader)


async def collect_women_techeu(*, generated_at: datetime) -> SourceCollectionResult:
    async def loader():
        return await collect_women_techeu_opportunities(now=generated_at)
    return await _collect_innovation("women_techeu", loader)


async def collect_innosuisse(*, generated_at: datetime) -> SourceCollectionResult:
    async def loader():
        return await collect_innosuisse_startup_opportunities(now=generated_at)
    return await _collect_innovation("innosuisse_startup_innovation", loader)


async def collect_innobooster(*, generated_at: datetime) -> SourceCollectionResult:
    async def loader():
        return await collect_innobooster_opportunities(now=generated_at)
    return await _collect_innovation("innobooster", loader)


async def fetch_resilient_multi_source_public_feed(
    *,
    generated_at: datetime | None = None,
    eu_page_size: int = 100,
    html_source_limit: int = 20,
) -> tuple[PublicOpportunityFeed, tuple[SourceCollectionResult, ...]]:
    generated_at = generated_at or datetime.now(timezone.utc)
    results = await asyncio.gather(
        collect_eu(generated_at=generated_at, page_size=eu_page_size),
        collect_ukri(limit=html_source_limit),
        collect_nihr(limit=html_source_limit),
        collect_wellcome(limit=html_source_limit),
        collect_science_for_africa(limit=html_source_limit),
        collect_idrc(limit=html_source_limit),
        collect_grand_challenges_canada_watch(),
        collect_fogarty(limit=html_source_limit),
        collect_eurostars(limit=min(html_source_limit, 5), generated_at=generated_at),
        collect_women_techeu(generated_at=generated_at),
        collect_innosuisse(generated_at=generated_at),
        collect_innobooster(generated_at=generated_at),
    )
    combined: list[Opportunity] = []
    for result in results:
        combined.extend(result.opportunities)
    source_health = [source_health_from_collection(result, checked_at=generated_at) for result in results]
    return build_public_feed(combined, generated_at=generated_at, source_health=source_health), tuple(results)
