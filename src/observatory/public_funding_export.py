from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl

from .funding_extract import ExtractedFundingRecord


class SourceState(str, Enum):
    structured_beta = "structured_beta"
    structured_beta_detail = "structured_beta_detail"
    index_only = "index_only"
    partial = "partial"
    manual_verify = "manual_verify"


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


def export_structured_record(record: ExtractedFundingRecord, *, source_state: SourceState, source_checked_at: str) -> PublicFundingRecord:
    if source_state not in {SourceState.structured_beta, SourceState.structured_beta_detail}:
        raise ValueError("only structured beta source states may publish structured call fields")
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


def export_link_only(*, funder: str, title: str, primary_url: str, source_state: SourceState, source_checked_at: str) -> PublicFundingRecord:
    if source_state in {SourceState.structured_beta, SourceState.structured_beta_detail}:
        raise ValueError("structured beta sources must use the structured export path")
    return PublicFundingRecord(funder=funder, title=title, primary_url=primary_url, source_state=source_state, source_checked_at=source_checked_at)
