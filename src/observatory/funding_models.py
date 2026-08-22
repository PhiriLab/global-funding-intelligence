from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

CareerStage = Literal["student", "early_career", "mid_career", "senior", "independent", "any"]
DeadlineStage = Literal["expression_of_interest", "outline", "preliminary", "full_application", "interview", "decision", "other"]


class OpportunityStatus(str, Enum):
    forecast = "forecast"
    upcoming = "upcoming"
    open = "open"
    rolling = "rolling"
    closed = "closed"
    unknown = "unknown"


class FundingDeadline(BaseModel):
    stage: DeadlineStage
    due_at: datetime
    label: str | None = None
    source_text: str | None = None

    @field_validator("due_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("deadline must be timezone-aware")
        return value


class Opportunity(BaseModel):
    source_id: str
    external_id: str | None = None
    identity_key: str | None = None
    title: str
    funder: str
    programme: str | None = None
    primary_url: HttpUrl
    status: OpportunityStatus = OpportunityStatus.unknown
    summary: str | None = None
    sectors: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    applicant_types: list[str] = Field(default_factory=list)
    career_stages: list[CareerStage] = Field(default_factory=list)
    years_since_phd_min: float | None = Field(default=None, ge=0)
    years_since_phd_max: float | None = Field(default=None, ge=0)
    eligible_countries: list[str] = Field(default_factory=list)
    excluded_countries: list[str] = Field(default_factory=list)
    lead_countries: list[str] = Field(default_factory=list)
    partner_countries: list[str] = Field(default_factory=list)
    oda_only: bool | None = None
    eligible_income_groups: list[Literal["LIC", "LMIC", "UMIC", "HIC"]] = Field(default_factory=list)
    global_majority_access: Literal["direct", "partner_only", "restricted", "unclear", "not_applicable"] = "unclear"
    lead_location_rule: str | None = None
    consortium_required: bool | None = None
    local_partner_required: bool | None = None
    equity_or_lmic_requirement: str | None = None
    currency: str | None = None
    min_award: float | None = None
    max_award: float | None = None
    total_fund: float | None = None
    opening_at: datetime | None = None
    closing_at: datetime | None = None
    deadlines: list[FundingDeadline] = Field(default_factory=list)
    rolling: bool = False
    trl_min: int | None = Field(default=None, ge=1, le=9)
    trl_max: int | None = Field(default=None, ge=1, le=9)
    source_checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_updated_at: datetime | None = None
    provenance_note: str | None = None
    raw_source_hash: str | None = None

    @field_validator("title", "funder", "source_id")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("eligible_countries", "excluded_countries", "lead_countries", "partner_countries")
    @classmethod
    def normalise_country_codes(cls, values: list[str]) -> list[str]:
        normalised = [value.strip().upper() for value in values if value and value.strip()]
        bad = [value for value in normalised if len(value) != 2 or not value.isalpha()]
        if bad:
            raise ValueError(f"country values must use ISO-3166 alpha-2 codes: {bad}")
        return sorted(set(normalised))

    @model_validator(mode="after")
    def validate_amounts_and_dates(self) -> "Opportunity":
        if self.min_award is not None and self.max_award is not None and self.min_award > self.max_award:
            raise ValueError("min_award cannot exceed max_award")
        if self.opening_at and self.closing_at and self.opening_at > self.closing_at:
            raise ValueError("opening_at cannot be after closing_at")
        if self.trl_min and self.trl_max and self.trl_min > self.trl_max:
            raise ValueError("trl_min cannot exceed trl_max")
        if self.years_since_phd_min is not None and self.years_since_phd_max is not None and self.years_since_phd_min > self.years_since_phd_max:
            raise ValueError("years_since_phd_min cannot exceed years_since_phd_max")
        return self

    def next_actionable_deadline(self, now: datetime | None = None) -> datetime | None:
        now = now or datetime.now(timezone.utc)
        future = sorted(d.due_at for d in self.deadlines if d.stage not in {"decision", "interview"} and d.due_at >= now)
        if future:
            return future[0]
        if self.closing_at and self.closing_at >= now:
            return self.closing_at
        return None


class ApplicantProfile(BaseModel):
    country: str
    organisation_type: str
    sectors: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    career_stage: CareerStage | None = None
    years_since_phd: float | None = Field(default=None, ge=0)
    trl: int | None = Field(default=None, ge=1, le=9)
    income_group: Literal["LIC", "LMIC", "UMIC", "HIC"] | None = None
    oda_eligible: bool | None = None
    can_form_consortium: bool = True
    has_required_local_partner: bool = False

    @field_validator("country")
    @classmethod
    def normalise_country(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise ValueError("country must use ISO-3166 alpha-2")
        return value


class FundingScore(BaseModel):
    eligibility: float = Field(ge=0, le=100)
    strategic_fit: float = Field(ge=0, le=100)
    accessibility: float = Field(ge=0, le=100)
    deadline_feasibility: float = Field(ge=0, le=100)
    award_value: float = Field(ge=0, le=100)
    burden: float = Field(ge=0, le=100, description="100 means low burden")
    source_confidence: float = Field(ge=0, le=100)
    overall: float = Field(ge=0, le=100)
    decision: Literal["apply", "partner", "watch", "verify", "skip"]
    eligibility_gate: Literal["pass", "fail", "uncertain"] = "uncertain"
    participation_route: Literal["lead", "partner", "unknown", "ineligible"] = "unknown"
    unknowns: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


_SATISFIED, _VIOLATED, _UNKNOWN = "satisfied", "violated", "unknown"


def _participation_route(opportunity: Opportunity, applicant: ApplicantProfile) -> str:
    country = applicant.country
    if country in opportunity.excluded_countries:
        return "ineligible"
    if opportunity.lead_countries or opportunity.partner_countries:
        if country in opportunity.lead_countries:
            return "lead"
        if country in opportunity.partner_countries:
            return "partner"
        return "ineligible"
    if opportunity.eligible_countries:
        return "lead" if country in opportunity.eligible_countries else "ineligible"
    return "unknown"


def _country_state(opportunity: Opportunity, applicant: ApplicantProfile) -> str:
    route = _participation_route(opportunity, applicant)
    if route in {"lead", "partner"}:
        return _SATISFIED
    if route == "ineligible":
        return _VIOLATED
    return _UNKNOWN


def _membership_state(allowed: list[str], value: str) -> str:
    if not allowed:
        return _UNKNOWN
    return _SATISFIED if value in allowed else _VIOLATED


def _flag_state(required: bool | None, applicant_has: bool) -> str:
    if required is None:
        return _UNKNOWN
    if not required:
        return _SATISFIED
    return _SATISFIED if applicant_has else _VIOLATED


def _oda_state(opportunity: Opportunity, applicant: ApplicantProfile) -> str:
    if opportunity.oda_only is None:
        return _UNKNOWN
    if opportunity.oda_only is False:
        return _SATISFIED
    if applicant.oda_eligible is None:
        return _UNKNOWN
    return _SATISFIED if applicant.oda_eligible else _VIOLATED


def _income_state(opportunity: Opportunity, applicant: ApplicantProfile) -> str:
    if not opportunity.eligible_income_groups:
        return _UNKNOWN
    if applicant.income_group is None:
        return _UNKNOWN
    return _SATISFIED if applicant.income_group in opportunity.eligible_income_groups else _VIOLATED


def _career_state(opportunity: Opportunity, applicant: ApplicantProfile) -> str:
    if not opportunity.career_stages and opportunity.years_since_phd_min is None and opportunity.years_since_phd_max is None:
        return _UNKNOWN
    if opportunity.career_stages and "any" not in opportunity.career_stages:
        if applicant.career_stage is None:
            return _UNKNOWN
        if applicant.career_stage not in opportunity.career_stages:
            return _VIOLATED
    if opportunity.years_since_phd_min is not None or opportunity.years_since_phd_max is not None:
        if applicant.years_since_phd is None:
            return _UNKNOWN
        if opportunity.years_since_phd_min is not None and applicant.years_since_phd < opportunity.years_since_phd_min:
            return _VIOLATED
        if opportunity.years_since_phd_max is not None and applicant.years_since_phd > opportunity.years_since_phd_max:
            return _VIOLATED
    return _SATISFIED


def score_opportunity(opportunity: Opportunity, applicant: ApplicantProfile, now: datetime | None = None) -> FundingScore:
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    blockers: list[str] = []
    unknowns: list[str] = []
    participation_route = _participation_route(opportunity, applicant)
    criteria = [
        ("country eligibility", _country_state(opportunity, applicant)),
        ("organisation type", _membership_state(opportunity.applicant_types, applicant.organisation_type)),
        ("consortium requirement", _flag_state(opportunity.consortium_required, applicant.can_form_consortium)),
        ("local partner requirement", _flag_state(opportunity.local_partner_required, applicant.has_required_local_partner)),
    ]
    if opportunity.oda_only is not None:
        criteria.append(("ODA eligibility", _oda_state(opportunity, applicant)))
    if opportunity.eligible_income_groups:
        criteria.append(("income-group eligibility", _income_state(opportunity, applicant)))
    if opportunity.career_stages or opportunity.years_since_phd_min is not None or opportunity.years_since_phd_max is not None:
        criteria.append(("career-stage eligibility", _career_state(opportunity, applicant)))
    eligibility = 100.0
    for label, state in criteria:
        if state == _VIOLATED:
            eligibility -= 25; blockers.append(label)
        elif state == _UNKNOWN:
            eligibility -= 12; unknowns.append(label)
    sector_overlap = len(set(map(str.lower, applicant.sectors)) & set(map(str.lower, opportunity.sectors)))
    stage_overlap = len(set(map(str.lower, applicant.stages)) & set(map(str.lower, opportunity.stages)))
    strategic_fit = min(100.0, 40 + sector_overlap * 30 + stage_overlap * 20)
    accessibility_map = {"direct": 100.0, "partner_only": 65.0, "restricted": 20.0, "unclear": 45.0, "not_applicable": 70.0}
    accessibility = accessibility_map[opportunity.global_majority_access]
    actionable_deadline = opportunity.next_actionable_deadline(now)
    if actionable_deadline:
        days = (actionable_deadline - now).total_seconds() / 86400
        deadline_feasibility = min(100.0, max(20.0, days * 2.5))
    elif opportunity.closing_at and opportunity.closing_at < now:
        deadline_feasibility = 10.0
    else:
        deadline_feasibility = 85.0 if opportunity.rolling else 60.0
    if opportunity.max_award is None: award_value = 55.0
    elif opportunity.max_award >= 1_000_000: award_value = 100.0
    elif opportunity.max_award >= 250_000: award_value = 85.0
    elif opportunity.max_award >= 50_000: award_value = 70.0
    else: award_value = 55.0
    burden = 55.0
    if opportunity.consortium_required: burden -= 15
    if opportunity.local_partner_required: burden -= 10
    if opportunity.status in {OpportunityStatus.forecast, OpportunityStatus.upcoming, OpportunityStatus.rolling}: burden += 10
    burden = min(100.0, max(0.0, burden))
    age_hours = max(0.0, (now - opportunity.source_checked_at).total_seconds() / 3600)
    source_confidence = max(40.0, 100.0 - min(age_hours, 168) * 0.35)
    overall = round(eligibility * 0.28 + strategic_fit * 0.22 + accessibility * 0.14 + deadline_feasibility * 0.12 + award_value * 0.08 + burden * 0.06 + source_confidence * 0.10, 1)
    if blockers: eligibility_gate = "fail"
    elif unknowns or opportunity.global_majority_access == "unclear" or participation_route == "unknown": eligibility_gate = "uncertain"
    else: eligibility_gate = "pass"
    if eligibility_gate == "fail": decision = "skip"
    elif eligibility_gate == "uncertain" or source_confidence < 60: decision = "verify"
    elif participation_route == "partner": decision = "partner"
    elif overall >= 78: decision = "apply"
    elif overall >= 62: decision = "watch"
    else: decision = "skip"
    if participation_route == "lead": reasons.append("country confirmed eligible to lead")
    elif participation_route == "partner": reasons.append("country confirmed eligible as partner, not lead")
    if sector_overlap: reasons.append("sector match")
    if opportunity.global_majority_access == "direct": reasons.append("direct Global Majority access")
    if unknowns: reasons.append("verify before applying: " + ", ".join(unknowns) + " not stated by source")
    return FundingScore(eligibility=max(0.0, eligibility), strategic_fit=strategic_fit, accessibility=accessibility, deadline_feasibility=deadline_feasibility, award_value=award_value, burden=burden, source_confidence=source_confidence, overall=overall, decision=decision, eligibility_gate=eligibility_gate, participation_route=participation_route, unknowns=unknowns, reasons=reasons, blockers=blockers)
