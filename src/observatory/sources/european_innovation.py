from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from observatory.funding_adapter import canonicalise_url, fetch_primary_html
from observatory.funding_extract import visible_lines
from observatory.funding_models import Opportunity, OpportunityStatus

EUROSTARS_INDEX = "https://www.eurekanetwork.org/programmes-and-calls/eurostars/"
WOMEN_TECHEU_ACTIVE = "https://womentecheurope.eu/active-calls/"


class _H1Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._inside = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "h1":
            self._inside = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "h1":
            self._inside = False

    def handle_data(self, data: str) -> None:
        if self._inside:
            self.parts.append(data)

    def title(self) -> str | None:
        value = " ".join(" ".join(self.parts).split()).strip()
        return value or None


def _title(html: str, fallback: str) -> str:
    parser = _H1Parser()
    parser.feed(html)
    return parser.title() or fallback


def _normalised_text(lines: list[str]) -> str:
    return " ".join(" ".join(lines).split())


def _label_value(lines: list[str], label: str) -> str | None:
    wanted = label.casefold().rstrip(":")
    for index, line in enumerate(lines):
        lower = line.casefold().strip()
        if lower in {wanted, wanted + ":"}:
            return lines[index + 1].strip() if index + 1 < len(lines) else None
        prefix = wanted + ":"
        if lower.startswith(prefix):
            value = line[len(prefix):].strip()
            return value or (lines[index + 1].strip() if index + 1 < len(lines) else None)
    return None


def _parse_brussels_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    clean = value.replace("CE(S)T", "").replace("CEST", "").replace("CET", "")
    clean = re.sub(r"\s+", " ", clean).strip(" ,")
    clean = re.sub(r"\bat\b", "", clean, flags=re.I)
    clean = re.sub(r"\s+", " ", clean).strip(" ,")
    for fmt in (
        "%d %B %Y, %I:%M %p",
        "%d %B %Y %I:%M %p",
        "%d %B %Y, %H:%M",
        "%d %B %Y %H:%M",
        "%d %B %Y",
    ):
        try:
            local = datetime.strptime(clean, fmt).replace(tzinfo=ZoneInfo("Europe/Brussels"))
            return local.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _status_for_window(opening_at: datetime | None, closing_at: datetime | None, now: datetime) -> OpportunityStatus:
    if opening_at and now < opening_at:
        return OpportunityStatus.upcoming
    if closing_at and now > closing_at:
        return OpportunityStatus.closed
    return OpportunityStatus.open


def _is_eurostars_call_url(url: str) -> bool:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() != "www.eurekanetwork.org":
        return False
    path = parsed.path.rstrip("/")
    return path.startswith("/programmes-and-calls/eurostars/eurostars-call-for-projects-")


async def discover_eurostars_calls(limit: int = 5) -> tuple[str, ...]:
    if limit <= 0:
        return ()
    snapshot = await fetch_primary_html(
        "eurostars",
        EUROSTARS_INDEX,
        keywords=("eurostars", "call", "projects"),
    )
    found: list[str] = []
    seen: set[str] = set()
    for candidate in snapshot.candidate_links:
        if not _is_eurostars_call_url(candidate):
            continue
        canonical = canonicalise_url(candidate)
        if canonical in seen:
            continue
        seen.add(canonical)
        found.append(canonical)
        if len(found) >= limit:
            break
    return tuple(found)


async def fetch_eurostars_call(url: str, *, now: datetime | None = None) -> Opportunity:
    now = now or datetime.now(timezone.utc)
    snapshot = await fetch_primary_html(
        "eurostars",
        url,
        keywords=("eurostars", "call", "fund", "apply", "country"),
    )
    lines = visible_lines(snapshot.text)
    text = _normalised_text(lines)
    opening_at = _parse_brussels_datetime(_label_value(lines, "Start Date"))
    closing_at = _parse_brussels_datetime(_label_value(lines, "End Date"))
    status = _status_for_window(opening_at, closing_at, now)

    consortium_required = True if "project consortium must have an innovative sme in the leading role" in text.casefold() else None
    applicant_types: list[str] = []
    lowered = text.casefold()
    for marker, value in (
        ("innovative sme", "innovative SME"),
        ("large companies", "large company"),
        ("universities", "university"),
        ("research organisations", "research organisation"),
    ):
        if marker in lowered:
            applicant_types.append(value)

    south_africa = "south africa" in lowered
    uk = "united kingdom" in lowered
    gm_access = "direct" if south_africa else "unclear"
    route_note = (
        "Eurostars funding is administered by national/regional funding bodies; eligible organisations, activities, rates and maxima vary by country. "
        "The consortium must be led by an innovative SME and collaborate internationally."
    )
    if south_africa and uk:
        route_note += " The authoritative call page lists both South Africa and the United Kingdom among participating countries."

    return Opportunity(
        source_id="eurostars",
        external_id=urlparse(snapshot.final_url).path.rstrip("/").split("/")[-1],
        title=_title(snapshot.text, "Eurostars call for projects"),
        funder="Eureka / national Eurostars funding bodies",
        programme="Eurostars",
        primary_url=snapshot.final_url,
        status=status,
        applicant_types=applicant_types,
        consortium_required=consortium_required,
        lead_location_rule="Consortium led by an innovative SME in a participating Eurostars country; national funding rules apply to each participant.",
        global_majority_access=gm_access,
        opening_at=opening_at,
        closing_at=closing_at,
        source_checked_at=now,
        provenance_note=route_note,
        raw_source_hash=snapshot.content_hash,
    )


async def collect_eurostars_opportunities(*, limit: int = 5, now: datetime | None = None) -> tuple[Opportunity, ...]:
    urls = await discover_eurostars_calls(limit=limit)
    opportunities: list[Opportunity] = []
    for url in urls:
        item = await fetch_eurostars_call(url, now=now)
        if item.status != OpportunityStatus.closed:
            opportunities.append(item)
    return tuple(opportunities)


async def fetch_women_techeu_opportunity(*, now: datetime | None = None) -> Opportunity:
    now = now or datetime.now(timezone.utc)
    snapshot = await fetch_primary_html(
        "women_techeu",
        WOMEN_TECHEU_ACTIVE,
        keywords=("call", "eligibility", "proposal", "women", "tech"),
    )
    lines = visible_lines(snapshot.text)
    text = _normalised_text(lines)
    lowered = text.casefold()

    opening_match = re.search(r"Eligibility Strand.*?Opening date:\s*([0-9]{1,2} [A-Za-z]+ 20[0-9]{2})", text, flags=re.I)
    final_match = re.search(r"Final cut-off:\s*([0-9]{1,2} [A-Za-z]+ 20[0-9]{2}) at ([0-9]{1,2}:[0-9]{2})", text, flags=re.I)
    opening_at = _parse_brussels_datetime(opening_match.group(1) if opening_match else None)
    closing_at = _parse_brussels_datetime(f"{final_match.group(1)} {final_match.group(2)} CEST" if final_match else None)

    award_match = re.search(r"€\s*([0-9][0-9,]*)\s*in non-dilutive funding", text, flags=re.I)
    if not award_match:
        award_match = re.search(r"€\s*([0-9][0-9,]*)\s*(?:grants|grant)", text, flags=re.I)
    max_award = float(award_match.group(1).replace(",", "")) if award_match else None

    full_deadlines = re.findall(
        r"Submission deadline [0-9]+:\s*([0-9]{1,2} [A-Za-z]+ 20[0-9]{2}) at ([0-9]{1,2}:[0-9]{2})",
        text,
        flags=re.I,
    )
    deadline_text = "; ".join(f"{date} {clock} Brussels time" for date, clock in full_deadlines[:4])

    if "call is open" in lowered or "eligibility strand" in lowered:
        status = OpportunityStatus.rolling
    else:
        status = _status_for_window(opening_at, closing_at, now)

    two_stage = "two-stage application process" in lowered or "eligibility strand" in lowered and "full proposal" in lowered
    provenance = (
        "Women TechEU uses a two-stage process: applicants first pass the Eligibility Strand and only eligible applicants may submit a Full Proposal. "
        "The source states that the scheme supports women-led early-stage deep-tech startups and provides non-dilutive funding."
    )
    if deadline_text:
        provenance += f" Published Full Proposal deadlines: {deadline_text}."

    return Opportunity(
        source_id="women_techeu",
        external_id="women-techeu-2-eic-2026-2028",
        title="Women TechEU 2 EIC — women-led early-stage deep-tech startups",
        funder="Women TechEU / European Union",
        programme="Women TechEU 2 EIC",
        primary_url=snapshot.final_url,
        status=status,
        applicant_types=["early-stage deep-tech startup"],
        consortium_required=False if two_stage else None,
        lead_location_rule="Company must satisfy the current Women TechEU establishment, age, women-founder ownership and leadership rules; verify the live Guidelines/FAQ.",
        currency="EUR" if max_award is not None else None,
        max_award=max_award,
        opening_at=opening_at,
        closing_at=closing_at,
        rolling=True,
        global_majority_access="restricted",
        source_checked_at=now,
        provenance_note=provenance,
        raw_source_hash=snapshot.content_hash,
    )


async def collect_women_techeu_opportunities(*, now: datetime | None = None) -> tuple[Opportunity, ...]:
    item = await fetch_women_techeu_opportunity(now=now)
    return () if item.status == OpportunityStatus.closed else (item,)
