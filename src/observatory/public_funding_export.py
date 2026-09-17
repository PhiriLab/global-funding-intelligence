from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl

from .funding_extract import ExtractedFundingRecord


class SourceState(str, Enum):
    structured_beta = "structured_beta"
    structured_beta_detail = "structured_beta_detail"
    index_only = "index_only"
    partial = "partial"
    manual_verify = "manual_verify"


DEFAULT_SOURCE_REGISTRY = Path("config/funder_ingestion.yaml")
INNOVATION_SOURCE_REGISTRY = Path("config/innovation_ingestion.yaml")
STRUCTURED_STATES = {SourceState.structured_beta, SourceState.structured_beta_detail}


class PublicFundingRecord(BaseModel):
    funder: str
    title: str
    primary_url: HttpUrl
    source_state: SourceState
    source_checked_at: str
    deadline: str | None = None
    deadline_warning: str | None = None
    currency: str | None = None
    min_award: float | None = None
    max_award: float | None = None
    total_fund: float | None = None
    budget_text: str | None = None
    eligibility: str = "Not determined — verify at source"
    warnings: list[str] = Field(default_factory=list)


def _registry_paths(path: str | Path) -> tuple[Path, ...]:
    requested = Path(path)
    if requested == DEFAULT_SOURCE_REGISTRY and INNOVATION_SOURCE_REGISTRY.exists():
        return DEFAULT_SOURCE_REGISTRY, INNOVATION_SOURCE_REGISTRY
    return (requested,)


def load_source_state_registry(path: str | Path = DEFAULT_SOURCE_REGISTRY) -> dict[str, SourceState]:
    """Load trusted publication states from reviewed ingestion manifests.

    The legacy/main manifest remains the default system of record. When the default
    registry is used, the separately reviewed innovation registry is merged in.
    Custom registry paths used by tests/tools remain isolated. Duplicate source ids
    fail closed so a secondary manifest cannot silently override an existing source.
    """
    registry: dict[str, SourceState] = {}
    for registry_path in _registry_paths(path):
        raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        for source_id, item in (raw.get("sources") or {}).items():
            if source_id in registry:
                raise ValueError(f"duplicate source id across trusted ingestion registries: {source_id}")
            try:
                registry[source_id] = SourceState(item["automation"])
            except (KeyError, ValueError, TypeError) as exc:
                raise ValueError(f"invalid or missing automation state for source: {source_id}") from exc
    return registry


def resolve_source_state(source_id: str, path: str | Path = DEFAULT_SOURCE_REGISTRY) -> SourceState:
    registry = load_source_state_registry(path)
    try:
        return registry[source_id]
    except KeyError as exc:
        raise ValueError(f"source is not present in trusted ingestion registry: {source_id}") from exc


def export_structured_record(
    record: ExtractedFundingRecord,
    *,
    source_checked_at: str,
    registry_path: str | Path = DEFAULT_SOURCE_REGISTRY,
) -> PublicFundingRecord:
    source_state = resolve_source_state(record.source_id, registry_path)
    if source_state not in STRUCTURED_STATES:
        raise ValueError(
            f"source {record.source_id!r} is {source_state.value!r}; "
            "only trusted structured beta source states may publish structured call fields"
        )
    warnings = list(record.extraction_warnings)
    deadline_warning = next((w for w in warnings if "deadline" in w.lower() or "closing" in w.lower() or "timezone" in w.lower()), None)
    return PublicFundingRecord(
        funder=record.funder or record.source_id,
        title=record.title,
        primary_url=record.primary_url,
        source_state=source_state,
        source_checked_at=source_checked_at,
        deadline=record.closing_at.isoformat() if record.closing_at else None,
        deadline_warning=deadline_warning,
        currency=record.currency,
        min_award=record.min_award,
        max_award=record.max_award,
        total_fund=record.total_fund,
        budget_text=record.budget_text,
        warnings=warnings,
    )


def export_link_only(
    *,
    source_id: str,
    funder: str,
    title: str,
    primary_url: str,
    source_checked_at: str,
    registry_path: str | Path = DEFAULT_SOURCE_REGISTRY,
) -> PublicFundingRecord:
    source_state = resolve_source_state(source_id, registry_path)
    if source_state in STRUCTURED_STATES:
        raise ValueError(f"source {source_id!r} is structured beta and must use the structured export path")
    return PublicFundingRecord(
        funder=funder,
        title=title,
        primary_url=primary_url,
        source_state=source_state,
        source_checked_at=source_checked_at,
    )
