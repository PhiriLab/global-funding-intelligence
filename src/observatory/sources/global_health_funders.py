from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from observatory.funding_adapter import FundingSnapshot, canonicalise_url, fetch_primary_html
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


class _OpenCallsParser(HTMLParser):
    """Capture links only while inside a heading-delimited Open calls section."""

    def __init__(self) -> None:
        super().__init__()
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self.in_open_calls = False
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        name = tag.lower()
        if name in {"h1", "h2", "h3"}:
            self._heading_tag = name
            self._heading_parts = []
        elif name == "a" and self.in_open_calls:
            href = next((value for key, value in attrs if key.lower() == "href" and value), None)
            if href:
                self.links.append(href)

    def handle_data(self, data: str) -> None:
        if self._heading_tag:
            self._heading_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if self._heading_tag == name:
            heading = " ".join("".join(self._heading_parts).split()).casefold()
            if heading == "open calls":
                self.in_open_calls = True
            elif self.in_open_calls and heading:
                self.in_open_calls = False
            self._heading_tag = None
            self._heading_parts = []


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


def _same_host_detail(source_id: str, raw_url: str) -> str | None:
    source = SOURCES[source_id]
    absolute = urljoin(source.url, raw_url)
    parsed = urlparse(absolute)
    source_host = (urlparse(source.url).hostname or "").lower().rstrip(".")
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host != source_host:
        return None
    try:
        canonical = canonicalise_url(absolute)
    except ValueError:
        return None
    path = urlparse(canonical).path.rstrip("/")
    if source_id == "science_for_africa":
        if not path.startswith("/funding/") or path == "/funding" or path.startswith("/funding-resources/"):
            return None
    elif source_id == "idrc":
        if not path.startswith("/en/funding/") or path in {"/en/funding/applying"}:
            return None
    else:
        return None
    return canonical


async def discover_science_for_africa_opportunities(limit: int = 20) -> tuple[str, ...]:
    if limit <= 0:
        return ()
    index = await fetch_funder_index("science_for_africa")
    found: list[str] = []
    seen: set[str] = set()
    for raw in index.candidate_links:
        detail = _same_host_detail("science_for_africa", raw)
        if detail and detail not in seen:
            seen.add(detail)
            found.append(detail)
            if len(found) >= limit:
                break
    return tuple(found)


async def discover_idrc_opportunities(limit: int = 20) -> tuple[str, ...]:
    if limit <= 0:
        return ()
    index = await fetch_funder_index("idrc")
    parser = _OpenCallsParser()
    parser.feed(index.text)
    found: list[str] = []
    seen: set[str] = set()
    for raw in parser.links:
        detail = _same_host_detail("idrc", raw)
        if detail and detail not in seen:
            seen.add(detail)
            found.append(detail)
            if len(found) >= limit:
                break
    return tuple(found)
