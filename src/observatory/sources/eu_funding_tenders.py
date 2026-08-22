from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from observatory.funding_models import Opportunity, OpportunityStatus

EU_SEARCH_API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text=***"
EU_PORTAL_BASE = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen"
_EU_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
MAX_JSON_BYTES = 2_000_000


@dataclass(frozen=True)
class EUFundingResult:
    raw: dict[str, Any]
    records: tuple[dict[str, Any], ...]


def _extract_records(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    candidates = (
        payload.get("results"), payload.get("result"), payload.get("items"),
        payload.get("documents"), payload.get("hits", {}).get("hits") if isinstance(payload.get("hits"), dict) else None,
    )
    for candidate in candidates:
        if isinstance(candidate, list):
            records: list[dict[str, Any]] = []
            for item in candidate:
                if isinstance(item, dict):
                    source = item.get("_source") if isinstance(item.get("_source"), dict) else item
                    records.append(source)
            return tuple(records)
    return ()


def _first(record: dict[str, Any], *keys: str):
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            if isinstance(value, list) and len(value) == 1:
                return value[0]
            return value
    return None


def _parse_api_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def normalise_eu_record(record: dict[str, Any]) -> Opportunity:
    identifier = str(_first(record, "identifier", "topicIdentifier", "callIdentifier", "id") or "eu-topic")
    title = str(_first(record, "title", "topicTitle", "name") or identifier)
    programme = _first(record, "frameworkProgrammeDescription", "frameworkProgramme", "programme", "programmePeriod")
    status_raw = str(_first(record, "statusDescription", "status", "callStatus") or "").lower()
    if "open" in status_raw:
        status = OpportunityStatus.open
    elif "forth" in status_raw or "upcoming" in status_raw:
        status = OpportunityStatus.upcoming
    elif "closed" in status_raw:
        status = OpportunityStatus.closed
    else:
        status = OpportunityStatus.unknown
    opening_at = _parse_api_date(_first(record, "openingDate", "startDate", "publicationDate"))
    closing_at = _parse_api_date(_first(record, "deadlineDate", "deadline", "closingDate"))
    ccm2_id = _first(record, "ccm2Id", "nid")
    provenance = "Normalised deterministically from the European Commission Funding & Tenders public REST API. Eligibility remains unverified until explicit structured rules are available."
    if _EU_IDENTIFIER.match(identifier):
        primary_url = f"{EU_PORTAL_BASE}/opportunities/topic-details/{quote(identifier, safe='')}"
    else:
        primary_url = f"{EU_PORTAL_BASE}/opportunities/topic-search"
        provenance += " Topic identifier was not in the expected format; linked to portal search rather than a derived deep link."
    if ccm2_id:
        provenance += f" ccm2Id={ccm2_id}."
    return Opportunity(source_id="eu_funding_tenders", external_id=identifier, title=title, funder="European Commission", programme=str(programme) if programme is not None else None, primary_url=primary_url, status=status, opening_at=opening_at, closing_at=closing_at, global_majority_access="unclear", source_checked_at=datetime.now(timezone.utc), provenance_note=provenance)


async def fetch_eu_open_calls(*, timeout: float = 30.0, page_size: int = 100) -> EUFundingResult:
    query = {"bool": {"must": [
        {"terms": {"type": ["1", "2", "8"]}},
        {"terms": {"status": ["31094501", "31094502", "31094503"]}},
        {"term": {"programmePeriod": "2021 - 2027"}},
    ]}}
    form = {"query": json.dumps(query, separators=(",", ":")), "pageSize": str(max(1, min(page_size, 1000))), "language": "en"}
    headers = {"User-Agent": "PhiriLab-Research-Observatory/1.0 funding-intelligence"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=False) as client:
        async with client.stream("POST", EU_SEARCH_API, data=form) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "json" not in content_type:
                raise ValueError(f"expected JSON from EU Funding & Tenders API, got {content_type or 'unknown'}")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                if len(body) + len(chunk) > MAX_JSON_BYTES:
                    raise ValueError("EU Funding & Tenders API response exceeds maximum allowed size")
                body.extend(chunk)
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("malformed JSON from EU Funding & Tenders API") from exc
    if not isinstance(payload, dict):
        raise ValueError("unexpected EU Funding & Tenders API response shape")
    return EUFundingResult(raw=payload, records=_extract_records(payload))
