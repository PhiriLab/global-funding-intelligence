from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_models import Opportunity, OpportunityStatus

FOGARTY_FUNDING_URL = "https://www.fic.nih.gov/Funding/Pages/Fogarty-Funding-Opps.aspx"
_ALLOWED_ANNOUNCEMENT_HOSTS = {"grants.nih.gov", "www.grants.gov", "grants.gov"}
_ANNOUNCEMENT_ID = re.compile(r"\b(?:PAR|RFA|PA)-[A-Z0-9]{2}-\d{3}\b", re.IGNORECASE)


@dataclass(frozen=True)
class FogartyFundingRow:
    deadline_text: str
    title: str
    announcement_url: str
    funding_type: str | None = None


class _FogartyTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_tr = False
        self.in_cell = False
        self.cells: list[str] = []
        self.cell_parts: list[str] = []
        self.links: list[str] = []
        self.rows: list[tuple[list[str], list[str]]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        name = tag.lower()
        if name == "tr":
            self.in_tr = True
            self.cells = []
            self.links = []
        elif self.in_tr and name in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []
        elif self.in_tr and self.in_cell and name == "a":
            href = next((value for key, value in attrs if key.lower() == "href" and value), None)
            if href:
                self.links.append(href)

    def handle_data(self, data: str) -> None:
        if self.in_tr and self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if self.in_tr and self.in_cell and name in {"td", "th"}:
            self.cells.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
            self.cell_parts = []
        elif self.in_tr and name == "tr":
            if self.cells:
                self.rows.append((list(self.cells), list(self.links)))
            self.in_tr = False
            self.in_cell = False


async def fetch_fogarty_funding() -> FundingSnapshot:
    return await fetch_primary_html(
        "fogarty",
        FOGARTY_FUNDING_URL,
        keywords=("fund", "award", "grant", "par-", "rfa-", "pa-"),
    )


def _announcement_url(raw: str) -> str | None:
    absolute = urljoin(FOGARTY_FUNDING_URL, raw)
    parsed = urlparse(absolute)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or host not in _ALLOWED_ANNOUNCEMENT_HOSTS:
        return None
    return absolute


def parse_fogarty_rows(html: str) -> tuple[FogartyFundingRow, ...]:
    parser = _FogartyTableParser()
    parser.feed(html)
    found: list[FogartyFundingRow] = []
    seen: set[str] = set()
    for cells, links in parser.rows:
        if len(cells) < 2 or not links:
            continue
        deadline_text = cells[0].strip()
        title = cells[1].strip()
        funding_type = cells[2].strip() if len(cells) > 2 and cells[2].strip() else None
        if not deadline_text or not title or not _ANNOUNCEMENT_ID.search(title):
            continue
        announcement = next((value for link in links if (value := _announcement_url(link))), None)
        if not announcement or announcement in seen:
            continue
        seen.add(announcement)
        found.append(FogartyFundingRow(deadline_text, title, announcement, funding_type))
    return tuple(found)


def normalise_fogarty_rows(rows: tuple[FogartyFundingRow, ...] | list[FogartyFundingRow]) -> tuple[Opportunity, ...]:
    opportunities: list[Opportunity] = []
    for row in rows:
        match = _ANNOUNCEMENT_ID.search(row.title)
        external_id = match.group(0).upper() if match else None
        opportunities.append(
            Opportunity(
                source_id="fogarty",
                external_id=external_id,
                title=row.title,
                funder="Fogarty International Center, NIH",
                programme=row.funding_type,
                primary_url=row.announcement_url,
                status=OpportunityStatus.open,
                global_majority_access="unclear",
                provenance_note=(
                    f"Fogarty current-funding table deadline: {row.deadline_text}. "
                    "The authoritative table publishes a calendar date without one universal submission timezone, so no clock time is invented. "
                    "Call-specific foreign-organisation and foreign-component eligibility remains unverified until authoritative announcement rules are structured."
                ),
            )
        )
    return tuple(opportunities)


async def collect_fogarty_opportunities(limit: int = 20) -> tuple[Opportunity, ...]:
    if limit <= 0:
        return ()
    snapshot = await fetch_fogarty_funding()
    return normalise_fogarty_rows(parse_fogarty_rows(snapshot.text))[:limit]
