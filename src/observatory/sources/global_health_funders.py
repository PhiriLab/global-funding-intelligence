from __future__ import annotations

from dataclasses import dataclass

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_extract import ExtractedFundingRecord, extract_structured_funding, to_opportunity
from observatory.funding_models import Opportunity


@dataclass(frozen=True)
class HTMLFunderSource:
    source_id: str
    url: str
    keywords: tuple[str, ...]
    structured: bool = False


SOURCES: dict[str, HTMLFunderSource] = {
    "science_for_africa": HTMLFunderSource("science_for_africa", "https://scienceforafrica.foundation/funding", ("fund", "grant", "call", "opportun", "challenge", "deltas"), True),
    "tdr_who": HTMLFunderSource("tdr_who", "https://tdr.who.int/grants", ("grant", "call", "fund", "application", "training"), False),
    "grand_challenges_canada": HTMLFunderSource("grand_challenges_canada", "https://www.grandchallenges.ca/apply-for-funding/", ("fund", "call", "request", "challenge", "application"), False),
    "idrc": HTMLFunderSource("idrc", "https://idrc-crdi.ca/en/funding", ("fund", "call", "grant", "award", "application"), True),
    "elrha": HTMLFunderSource("elrha", "https://www.elrha.org/funding-opportunities/", ("fund", "opportun", "call", "grant", "innovation", "research"), False),
    "cepi": HTMLFunderSource("cepi", "https://cepi.net/calls-for-proposals", ("call", "proposal", "fund", "award", "vaccine"), False),
    "novo_nordisk_foundation": HTMLFunderSource("novo_nordisk_foundation", "https://novonordiskfonden.dk/en/grants/", ("grant", "call", "application", "programme", "award"), False),
}


async def fetch_funder_index(source_id: str) -> FundingSnapshot:
    source = SOURCES[source_id]
    return await fetch_primary_html(source.source_id, source.url, keywords=source.keywords)


async def fetch_funder_opportunity(source_id: str, url: str) -> FundingSnapshot:
    source = SOURCES[source_id]
    return await fetch_primary_html(source.source_id, url, keywords=source.keywords)


async def extract_funder_opportunity(source_id: str, url: str) -> ExtractedFundingRecord:
    source = SOURCES[source_id]
    if not source.structured:
        raise ValueError(f"{source_id} is not approved for structured detail extraction; use its portal/PDF-specific path or manual verification")
    snapshot = await fetch_funder_opportunity(source_id, url)
    return extract_structured_funding(snapshot)


async def normalise_funder_opportunity(source_id: str, url: str) -> Opportunity:
    return to_opportunity(await extract_funder_opportunity(source_id, url))
