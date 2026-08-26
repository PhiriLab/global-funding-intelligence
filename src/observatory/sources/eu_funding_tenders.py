from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from observatory.funding_models import Opportunity, OpportunityStatus

EU_SEARCH_API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
EU_PORTAL_BASE = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen"
_EU_IDENTIFIER = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_EDCTP3_MARKERS = ("edctp3", "edctp 3", "global health edctp")
MAX_JSON_BYTES = 2_000_000


@dataclass(frozen=True)
class EUFundingResult:
    raw: dict[str, Any]
    records: tuple[dict[str, Any], ...]


def _flatten_search_result(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten the EC search wrapper while preserving useful top-level provenance.

    Current SEDIA search results expose most topic fields inside ``metadata`` as
    single-item arrays. Older fixtures/variants may already be flat, so this is
    deliberately backward compatible.
    """
    source = item.get("_source") if isinstance(item.get("_source"), dict) else item
    metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else None
    if metadata is None:
        return source
    flattened = dict(metadata)
    for key in ("reference", "url", "content", "type"):
        if source.get(key) not in (None, "", [], {}):
            flattened.setdefault(key, source[key])
    return flattened


def _extract_records(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    candidates = (
        payload.get("results"), payload.get("result"), payload.get("items"),
        payload.get("documents"), payload.get("hits", {}).get("hits") if isinstance(payload.get("hits"), dict) else None,
    )
    for candidate in candidates:
        if isinstance(candidate, list):
            return tuple(_flatten_search_result(item) for item in candidate if isinstance(item, dict))
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


def is_edctp3_record(record: dict[str, Any]) -> bool:
    values = (
        _first(record, "identifier", "topicIdentifier", "callIdentifier", "id"),
        _first(record, "title", "topicTitle", "name", "content"),
        _first(record, "programme", "programmePeriod", "frameworkProgrammeDescription", "frameworkProgramme"),
        _first(record, "callTitle", "callIdentifier"),
    )
    haystack = " ".join(str(value) for value in values if value not in (None, "", [], {})).lower()
    return any(marker in haystack for marker in _EDCTP3_MARKERS)


def normalise_eu_record(record: dict[str, Any]) -> Opportunity:
    identifier = str(_first(record, "identifier", "topicIdentifier", "callIdentifier", "reference", "id") or "eu-topic")
    title = str(_first(record, "title", "topicTitle", "name", "content") or identifier)
    programme = _first(record, "frameworkProgrammeDescription", "frameworkProgramme", "programme", "programmePeriod")
    status_raw = str(_first(record, "statusDescription", "status", "callStatus") or "").lower()
    if "open" in status_raw or status_raw in {"31094501", "31094502"}:
        status = OpportunityStatus.open
    elif "forth" in status_raw or "upcoming" in status_raw or status_raw == "31094503":
        status = OpportunityStatus.upcoming
    elif "closed" in status_raw:
        status = OpportunityStatus.closed
    else:
        status = OpportunityStatus.unknown
    opening_at = _parse_api_date(_first(record, "openingDate", "startDate", "publicationDate"))
    closing_at = _parse_api_date(_first(record, "deadlineDate", "deadline", "closingDate"))
    ccm2_id = _first(record, "ccm2Id", "callccm2Id", "nid")
    authoritative_url = _first(record, "url")
    provenance = "Normalised deterministically from the European Commission Funding & Tenders public Search API. Eligibility remains unverified until explicit structured rules are available."
    if isinstance(authoritative_url, str) and authoritative_url.startswith("https://ec.europa.eu/"):
        primary_url = authoritative_url
    elif _EU_IDENTIFIER.match(identifier):
        primary_url = f"{EU_PORTAL_BASE}/opportunities/topic-details/{quote(identifier, safe='')}"
    else:
        primary_url = f"{EU_PORTAL_BASE}/opportunities/topic-search"
        provenance += " Topic identifier was not in the expected format; linked to portal search rather than a derived deep link."
    if ccm2_id:
        provenance += f" ccm2Id={ccm2_id}."
    return Opportunity(source_id="eu_funding_tenders", external_id=identifier, title=title, funder="European Commission", programme=str(programme) if programme is not None else None, primary_url=primary_url, status=status, opening_at=opening_at, closing_at=closing_at, global_majority_access="unclear", source_checked_at=datetime.now(timezone.utc), provenance_note=provenance)


def normalise_edctp3_record(record: dict[str, Any]) -> Opportunity:
    opportunity = normalise_eu_record(record)
    note = (opportunity.provenance_note or "") + " Identified as Global Health EDCTP3 from authoritative EU programme metadata; call-specific applicant route remains unverified."
    return opportunity.model_copy(update={
        "source_id": "edctp3",
        "funder": "Global Health EDCTP3 Joint Undertaking",
        "provenance_note": note.strip(),
        "global_majority_access": "unclear",
    })


def normalise_eu_records(records: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[Opportunity, ...]:
    return tuple(normalise_edctp3_record(record) if is_edctp3_record(record) else normalise_eu_record(record) for record in records)


def normalise_edctp3_records(records: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[Opportunity, ...]:
    return tuple(normalise_edctp3_record(record) for record in records if is_edctp3_record(record))


async def fetch_eu_open_calls(*, timeout: float = 30.0, page_size: int = 100) -> EUFundingResult:
    query = {"bool": {"must": [
        {"terms": {"type": ["1", "2", "8"]}},
        {"terms": {"status": ["31094501", "31094502", "31094503"]}},
        {"term": {"programmePeriod": "2021 - 2027"}},
    ]}}
    size = max(1, min(page_size, 1000))
    params = {"apiKey": "SEDIA", "text": "***", "pageSize": str(size), "pageNumber": "1"}
    files = {
        "query": ("blob", json.dumps(query, separators=(",", ":")), "application/json"),
        "languages": ("blob", json.dumps(["en"], separators=(",", ":")), "application/json"),
        "displayLanguage": (None, "en"),
    }
    headers = {
        "User-Agent": "PhiriLab-GFI/1.0 (+https://phirilab.github.io/global-funding-intelligence/)",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://ec.europa.eu",
        "Referer": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
    }
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=False) as client:
        async with client.stream("POST", EU_SEARCH_API, params=params, files=files) as response:
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
