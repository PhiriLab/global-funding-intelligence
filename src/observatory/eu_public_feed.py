from __future__ import annotations

from datetime import datetime

from .public_opportunity_feed import PublicOpportunityFeed, build_public_feed, public_feed_json
from .sources.eu_funding_tenders import fetch_eu_open_calls, normalise_edctp3_records, normalise_eu_records


async def fetch_public_eu_feed(*, edctp3_only: bool = False, generated_at: datetime | None = None, page_size: int = 100) -> PublicOpportunityFeed:
    result = await fetch_eu_open_calls(page_size=page_size)
    opportunities = normalise_edctp3_records(result.records) if edctp3_only else normalise_eu_records(result.records)
    return build_public_feed(opportunities, generated_at=generated_at)


async def fetch_public_eu_feed_json(*, edctp3_only: bool = False, generated_at: datetime | None = None, page_size: int = 100, indent: int | None = 2) -> str:
    result = await fetch_eu_open_calls(page_size=page_size)
    opportunities = normalise_edctp3_records(result.records) if edctp3_only else normalise_eu_records(result.records)
    return public_feed_json(opportunities, generated_at=generated_at, indent=indent)
