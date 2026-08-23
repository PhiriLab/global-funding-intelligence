from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from observatory.funding_adapter import FundingSnapshot, fetch_primary_html
from observatory.funding_models import Opportunity, OpportunityStatus

FOGARTY_FUNDING_URL = "https://www.fic.nih.gov/Funding/Pages/Fogarty-Funding-Opps.aspx"
_ALLOWED_ANNOUNCEMENT_HOSTS = {"grants.nih.gov", "www.grants.gov", "grants.gov"}


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
        self.in_td = False
        self.cells: list[str] = []
        self.cell_parts: list[str] = []
        self.cell_links: list[str] = []
        self.rows: list[tuple[list[str], list[str]]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        name = tag.lower()
        if name == "tr":
            self.in_tr = True
            self.cells = []
            self.cell_links = []
        elif self.in_tr and name in {"td", "th"}:
            self.in_td = True
            self.cell_parts = []
        elif self.in_tr and self.in_td and name == "a":
            href = next((value for key, value in attrs if key.lower() == "href" and value), None)
            if href:
                self.cell_links.append(href)

    def handle_data(self, data: str) -> None:
        if self.in_tr and self.in_td:
            self.cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if self.in_tr and self.in_td and name in {"td", "th"}:
            text = " ".join("".join(self.cell_parts).split())
            self.cells.append(text)
            self.in_td = False
            self.cell_parts = []
        elif self.in_tr and name == "tr":
            if self.cells:
                self.rows.append((list(self.cells), list(self.cell_links)))
            self.in_tr = False
            self.in_td = False


def fetch_fogarty_funding() -> FundingSnapshot:
    raise RuntimeError("use async fetch_fogarty_funding_async")


async def fetch_fogarty_funding_async() -> FundingSnapshot:
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
        if not deadline_text or not title:
            continue
        announcement = next((_announcement_url(link) for link in links if _announcement_url(link)), None)
        if not announcement or announcement in seen:
            continue
        lower = title.lower()
        if not any(marker in lower for marker in ("par-", "rfa-", "pa-")):
            continue
        seen.add(announcement)
        found.append(FogartyFundingRow(deadline_text, title, announcement, funding_type))
    return tuple(found)


def normalise_fogarty_rows(rows: tuple[FogartyFundingRow, ...] | list[FogartyFundingRow]) -> tuple[Opportunity, ...]:
    opportunities: list[Opportunity] = []
    for row in rows:
        external_id = row.title.rsplit("(", 1)[-1].rstrip(")") if "(" in row.title else None
        opportunities.append(
            Opportunity(
                source_id="fogarty",
                external_id=external_id,
                title=row.title,
                funder="Fogarty International Center, NIH",
                programme=row.funding_type,
                primary_url=row.announcement_url,
                status=OpportunityStatus.open,
                deadline_text=row.deadline_text,
                global_majority_access="unclear",
                provenance_note=(
                    "Current opportunity and deadline date captured deterministically from the Fogarty International Center funding table. "
                    "The source publishes a calendar date without one universal submission timezone, so no clock time is invented. "
                    "Call-specific foreign-organisation and foreign-component eligibility remains unverified until authoritative announcement rules are structured."
                ),
            )
        )
    return tuple(opportunities)


async def collect_fogarty_opportunities(limit: int = 20) -> tuple[Opportunity, ...]:
    if limit <= 0:
        return ()
    snapshot = await fetch_fogarty_funding_async()
    return normalise_fogarty_rows(parse_fogarty_rows(snapshot.text))[:limit]
