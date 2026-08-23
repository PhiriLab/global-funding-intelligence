from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Literal
from zoneinfo import ZoneInfo

from .funding_adapter import FundingSnapshot
from .funding_models import Opportunity, OpportunityStatus


@dataclass(frozen=True)
class ExtractionProfile:
    default_funder: str | None = None
    funder_labels: tuple[str, ...] = ("Funders", "Funder")
    programme_labels: tuple[str, ...] = ("Programme",)
    status_labels: tuple[str, ...] = ("Opportunity status", "Status")
    funding_type_labels: tuple[str, ...] = ("Funding type",)
    total_fund_labels: tuple[str, ...] = ("Total fund",)
    award_range_labels: tuple[str, ...] = ("Award range",)
    maximum_award_labels: tuple[str, ...] = ("Maximum award", "Maximum Amount")
    opening_labels: tuple[str, ...] = ("Opening date",)
    closing_labels: tuple[str, ...] = ("Closing date", "Deadline for applications")


PROFILES: dict[str, ExtractionProfile] = {
    "ukri_funding_finder": ExtractionProfile(default_funder="UK Research and Innovation"),
    "nihr_funding": ExtractionProfile(default_funder="National Institute for Health and Care Research", funder_labels=("Funder", "Funders", "Funding organisation"), programme_labels=("Programme", "Funding programme", "Programme name"), status_labels=("Status", "Opportunity status", "Call status"), funding_type_labels=("Funding type", "Award type", "Scheme type"), total_fund_labels=("Total fund", "Total available funding"), award_range_labels=("Award range", "Funding available", "Funding amount"), maximum_award_labels=("Maximum award", "Maximum Amount", "Maximum funding"), opening_labels=("Opening date", "Call opens", "Applications open"), closing_labels=("Closing date", "Deadline for applications", "Application deadline", "Call closes")),
    "wellcome_funding": ExtractionProfile(default_funder="Wellcome", funder_labels=("Funder", "Funding organisation"), programme_labels=("Strategic programme", "Programme"), status_labels=("Status", "Scheme status"), funding_type_labels=("Funding type", "Scheme type"), total_fund_labels=("Total fund",), award_range_labels=("Funding amount", "Award amount", "Award range"), maximum_award_labels=("Maximum funding", "Maximum award"), opening_labels=("Applications open", "Opening date"), closing_labels=("Application deadline", "Full application deadline", "Closing date")),
    "science_for_africa": ExtractionProfile(default_funder="Science for Africa Foundation", programme_labels=("Programme", "Funding Overview"), status_labels=("Status", "Call status"), funding_type_labels=("Funding Type", "Funding type"), total_fund_labels=("Total fund", "Total funding"), award_range_labels=("Funding levels", "Funding amount", "Award range"), maximum_award_labels=("Maximum award", "Maximum funding"), opening_labels=("Launch date", "Opening date"), closing_labels=("Deadline", "Submission Deadline", "Application deadline")),
    "tdr_who": ExtractionProfile(default_funder="WHO/TDR", programme_labels=("Programme", "Grant scheme", "Call"), status_labels=("Status", "Call status"), funding_type_labels=("Funding type", "Type"), total_fund_labels=("Total fund", "Budget"), award_range_labels=("Funding", "Grant amount", "Award amount"), maximum_award_labels=("Maximum award", "Maximum grant"), opening_labels=("Opening date", "Call opens"), closing_labels=("Deadline", "Closing date", "Application deadline")),
    "idrc": ExtractionProfile(default_funder="International Development Research Centre (IDRC)", funder_labels=("Funded by", "Funder", "Funders"), programme_labels=("Programs", "Program", "Programme"), status_labels=("Status",), funding_type_labels=("Type", "Call For", "Funding type"), total_fund_labels=(), award_range_labels=("Funding amount", "Award range"), maximum_award_labels=("Maximum award", "Maximum funding"), opening_labels=("Launch date", "Opening date"), closing_labels=("Deadline", "Application deadline", "Closing date")),
    "elrha": ExtractionProfile(default_funder="Elrha", programme_labels=("Programme", "Funding programme", "Challenge"), status_labels=("Status", "Call status"), funding_type_labels=("Funding type", "Call type", "Type"), total_fund_labels=("Total funding", "Total fund", "Budget"), award_range_labels=("Funding available", "Grant size", "Funding amount"), maximum_award_labels=("Maximum award", "Maximum funding"), opening_labels=("Opening date", "Applications open"), closing_labels=("Deadline", "Application deadline", "Closing date")),
    "cepi": ExtractionProfile(default_funder="Coalition for Epidemic Preparedness Innovations (CEPI)", programme_labels=("Programme", "Call", "Area of interest"), status_labels=("Status", "Call status"), funding_type_labels=("Funding type", "Type"), total_fund_labels=("Total funding", "Budget", "Total fund"), award_range_labels=("Funding available", "Award amount", "Funding amount"), maximum_award_labels=("Maximum award", "Maximum funding"), opening_labels=("Opening date", "Launch date"), closing_labels=("Deadline", "Submission deadline", "Closing date")),
    "novo_nordisk_foundation": ExtractionProfile(default_funder="Novo Nordisk Foundation", programme_labels=("Programme", "Grant programme"), status_labels=("Status", "Application status"), funding_type_labels=("Grant type", "Funding type"), total_fund_labels=("Total fund", "Budget"), award_range_labels=("Amount", "Funding amount", "Grant amount"), maximum_award_labels=("Maximum amount", "Maximum award"), opening_labels=("Application opens", "Opening date"), closing_labels=("Application deadline", "Deadline", "Closing date")),
}


@dataclass(frozen=True)
class ExtractedFundingRecord:
    source_id: str
    primary_url: str
    title: str
    funder: str | None = None
    programme: str | None = None
    status: str | None = None
    funding_type: str | None = None
    currency: str | None = None
    min_award: float | None = None
    max_award: float | None = None
    total_fund: float | None = None
    budget_text: str | None = None
    opening_at: datetime | None = None
    closing_at: datetime | None = None
    rolling: bool = False
    eligibility_evidence: tuple[str, ...] = ()
    extraction_warnings: tuple[str, ...] = ()
    source_hash: str | None = None
    extraction_method: Literal["deterministic_html"] = "deterministic_html"


class _VisibleTextParser(HTMLParser):
    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "p", "li", "dt", "dd", "div", "section", "article", "br", "tr", "td", "th"}
    def __init__(self) -> None:
        super().__init__(); self.parts: list[str] = []; self._skip = 0
    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}: self._skip += 1
        elif not self._skip and tag in self.BLOCK_TAGS: self.parts.append("\n")
    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip: self._skip -= 1
        elif not self._skip and tag in self.BLOCK_TAGS: self.parts.append("\n")
    def handle_data(self, data: str) -> None:
        if not self._skip: self.parts.append(data)
    def lines(self) -> list[str]:
        text = "".join(self.parts).replace("\xa0", " ")
        return [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(); self.h1: list[str] = []; self.title: list[str] = []; self._capture: str | None = None
    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in {"h1", "title"}: self._capture = tag
    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == self._capture: self._capture = None
    def handle_data(self, data: str) -> None:
        if self._capture == "h1": self.h1.append(data)
        elif self._capture == "title": self.title.append(data)
    def best(self) -> str | None:
        h1 = re.sub(r"\s+", " ", " ".join(self.h1)).strip()
        if h1: return h1
        title = re.sub(r"\s+", " ", " ".join(self.title)).strip()
        return title or None


def visible_lines(html: str) -> list[str]:
    parser = _VisibleTextParser(); parser.feed(html); return parser.lines()


def _html_title(html: str) -> str | None:
    parser = _TitleParser(); parser.feed(html); return parser.best()


def _value_after_label(lines: list[str], label: str) -> str | None:
    label_l = label.lower().rstrip(":")
    for index, line in enumerate(lines):
        stripped = line.strip(); lower = stripped.lower()
        if lower == label_l or lower == f"{label_l}:": return lines[index + 1].strip() if index + 1 < len(lines) else None
        prefix = f"{label_l}:"
        if lower.startswith(prefix):
            value = stripped[len(prefix):].strip(); return value or (lines[index + 1].strip() if index + 1 < len(lines) else None)
    return None


def _first_label_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
    for label in labels:
        value = _value_after_label(lines, label)
        if value: return value
    return None


def _parse_money(value: str | None) -> tuple[str | None, float | None, float | None]:
    if not value: return None, None, None
    upper = value.upper()
    currency = "CAD" if "CAD" in upper else "GBP" if "GBP" in upper or "£" in value else "EUR" if "EUR" in upper or "€" in value else "USD" if "USD" in upper or "$" in value else None
    numbers: list[float] = []
    pattern = r"(CAD\s*|USD\s*|EUR\s*|GBP\s*|£|€|\$)?\s*([0-9]{1,3}(?:[ ,][0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:(million|m|thousand|k)\b)?"
    for symbol, digits, suffix in re.findall(pattern, value, flags=re.I):
        if not symbol and not suffix: continue
        number = float(digits.replace(",", "").replace(" ", "")); suffix = suffix.lower()
        if suffix in {"million", "m"}: number *= 1_000_000
        elif suffix in {"thousand", "k"}: number *= 1_000
        numbers.append(number)
    if not numbers: return currency, None, None
    if len(numbers) == 1: return currency, None, numbers[0]
    return currency, min(numbers), max(numbers)


def _timezone_for_label(value: str) -> timezone | ZoneInfo:
    upper = value.upper()
    if re.search(r"\bUK TIME\b", upper): return ZoneInfo("Europe/London")
    if re.search(r"\bET\b", upper): return ZoneInfo("America/New_York")
    if re.search(r"\bEDT\b", upper): return timezone(timedelta(hours=-4))
    if re.search(r"\bEST\b", upper): return timezone(timedelta(hours=-5))
    if re.search(r"\bEAT\b", upper): return ZoneInfo("Africa/Nairobi")
    match = re.search(r"\bGMT([+-]\d{1,2})\b", upper)
    if match: return timezone(timedelta(hours=int(match.group(1))))
    return timezone.utc


def _parse_date(value: str | None) -> tuple[datetime | None, bool]:
    if not value: return None, False
    clean = value.strip()
    if re.search(r"open\s*-?\s*no closing date|rolling", clean, flags=re.I): return None, True
    source_tz = _timezone_for_label(clean)
    clean = re.sub(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+", "", clean, flags=re.I)
    clean = re.sub(r"\b(UK time|ET|EDT|EST|EAT|UTC|GMT[+-]?\d*)\b", "", clean, flags=re.I).strip(" ,-")
    clean = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", clean, flags=re.I)
    clean = re.sub(r"(\d)(am|pm)\b", r"\1 \2", clean, flags=re.I)
    for fmt in ("%d %B %Y %I:%M%p", "%d %B %Y %I:%M %p", "%d %B %Y %H:%M", "%d %B %Y", "%d %b %Y", "%B %d, %Y - %H:%M", "%B %d, %Y %H:%M", "%B %d, %Y"):
        try:
            parsed = datetime.strptime(clean, fmt)
            if any(token in fmt for token in ("%H", "%I")):
                return parsed.replace(tzinfo=source_tz).astimezone(timezone.utc), False
            return parsed.replace(tzinfo=source_tz), False
        except ValueError:
            pass
    return None, False


def _eligibility_evidence(lines: list[str]) -> tuple[str, ...]:
    patterns = (r"\bmust be based\b", r"\bmust be employed\b", r"\beligib(?:le|ility)\b", r"\bapplicant(?:s)? must\b", r"\bprincipal applicant\b", r"\bby invitation only\b", r"\binvite only\b", r"\bconsortium\b", r"\bpartner\b", r"\bODA\b", r"\bLMIC\b", r"\blow[- ]and middle[- ]income\b", r"\bAfrican[- ]based\b", r"\bAfrican[- ]led\b")
    evidence: list[str] = []
    for line in lines:
        if any(re.search(pattern, line, flags=re.I) for pattern in patterns): evidence.append(line[:700])
    return tuple(dict.fromkeys(evidence[:25]))


def _idrc_budget_semantics(value: str | None) -> tuple[str | None, float | None, float | None, float | None, str | None]:
    if not value: return None, None, None, None, None
    currency, minimum, maximum = _parse_money(value)
    lower = value.lower()
    per_award = bool(re.search(r"\bper\s+(grant|consortium member|applicant|project|team)\b|\beach\b", lower))
    total_call = bool(re.search(r"\btotal\s+(call|programme|program)\s+budget\b|\btotal funding available\b", lower))
    mentions_total = "total" in lower
    if per_award and not mentions_total: return currency, minimum, maximum, None, None
    if total_call and not per_award: return currency, None, None, maximum, None
    return currency, None, None, None, "IDRC Budget field is semantically ambiguous; retained as evidence without assigning total_fund or max_award"


def extract_structured_funding(snapshot: FundingSnapshot) -> ExtractedFundingRecord:
    lines = visible_lines(snapshot.text); warnings: list[str] = []; profile = PROFILES.get(snapshot.source_id, ExtractionProfile())
    title = _value_after_label(lines, "Title") or _html_title(snapshot.text) or next((line for line in lines if len(line) >= 8 and not line.lower().startswith(("skip to", "menu", "search"))), "Untitled funding opportunity")
    funder = _first_label_value(lines, profile.funder_labels) or profile.default_funder
    programme = _first_label_value(lines, profile.programme_labels); status = _first_label_value(lines, profile.status_labels); funding_type = _first_label_value(lines, profile.funding_type_labels)
    total_currency, _, total_fund = _parse_money(_first_label_value(lines, profile.total_fund_labels)); award_label = _first_label_value(lines, profile.award_range_labels)
    if award_label: award_currency, min_award, max_award = _parse_money(award_label)
    else: award_currency, _, max_award = _parse_money(_first_label_value(lines, profile.maximum_award_labels)); min_award = None
    budget_text = None
    if snapshot.source_id == "idrc":
        budget_text = _value_after_label(lines, "Budget")
        budget_currency, budget_min, budget_max, budget_total, budget_warning = _idrc_budget_semantics(budget_text)
        if budget_min is not None or budget_max is not None: min_award, max_award = budget_min, budget_max
        if budget_total is not None: total_fund = budget_total
        if budget_warning: warnings.append(budget_warning)
        total_currency = total_currency or budget_currency
    currency = award_currency or total_currency
    opening_at, _ = _parse_date(_first_label_value(lines, profile.opening_labels)); closing_raw = _first_label_value(lines, profile.closing_labels); closing_at, rolling = _parse_date(closing_raw)
    if closing_raw and closing_at is None and not rolling: warnings.append(f"unparsed closing date: {closing_raw}")
    if max_award is not None and total_fund is not None and max_award == total_fund: warnings.append("max award equals total fund; verify whether this figure is a per-award maximum or the total call budget")
    if not status: warnings.append("status not extracted")
    return ExtractedFundingRecord(source_id=snapshot.source_id, primary_url=snapshot.final_url, title=title, funder=funder, programme=programme, status=status, funding_type=funding_type, currency=currency, min_award=min_award, max_award=max_award, total_fund=total_fund, budget_text=budget_text, opening_at=opening_at, closing_at=closing_at, rolling=rolling, eligibility_evidence=_eligibility_evidence(lines), extraction_warnings=tuple(warnings), source_hash=snapshot.content_hash)


def to_opportunity(record: ExtractedFundingRecord) -> Opportunity:
    status_map = {"open": OpportunityStatus.open, "upcoming": OpportunityStatus.upcoming, "forecast": OpportunityStatus.forecast, "closed": OpportunityStatus.closed}
    status = status_map.get((record.status or "").strip().lower(), OpportunityStatus.unknown)
    return Opportunity(source_id=record.source_id, title=record.title, funder=record.funder or record.source_id, programme=record.programme, primary_url=record.primary_url, status=status, currency=record.currency, min_award=record.min_award, max_award=record.max_award, total_fund=record.total_fund, opening_at=record.opening_at, closing_at=record.closing_at, rolling=record.rolling, source_checked_at=datetime.now().astimezone(), provenance_note="Deterministic extraction from primary source; eligibility evidence retained separately and not inferred.", raw_source_hash=record.source_hash)
