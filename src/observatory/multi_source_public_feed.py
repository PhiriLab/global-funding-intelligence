from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable

from .eu_public_feed import fetch_public_eu_feed
from .funding_extract import ExtractedFundingRecord, to_opportunity
from .funding_models import Opportunity, OpportunityStatus
from .public_opportunity_feed import PublicOpportunityFeed, build_public_feed
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
            global_majority_access=item.global_majority_access,
            source_checked_at=item.source_checked_at,
            provenance_note=item.provenance_note,
        )
        for item in eu_feed.opportunities
    ]

    ukri, nihr, wellcome = await asyncio.gather(
        collect_ukri(limit=html_source_limit),
        collect_nihr(limit=html_source_limit),
        collect_wellcome(limit=html_source_limit),
    )
    results = (ukri, nihr, wellcome)
    combined: list[Opportunity] = eu_opportunities
    for result in results:
        combined.extend(result.opportunities)
    return build_public_feed(combined, generated_at=generated_at), results
