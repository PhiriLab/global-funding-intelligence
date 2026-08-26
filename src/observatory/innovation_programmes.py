from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, HttpUrl, model_validator

ProgrammeClass = Literal[
    "direct_funding",
    "eu_programme_pipeline",
    "cascade_funding",
    "watcher",
    "meta_source",
    "ecosystem_access",
]
Priority = Literal["P1", "P2", "P3"]
GlobalMajorityRelevance = Literal["high", "mixed", "low"]
FundingInstrument = Literal[
    "grant",
    "non_dilutive_grant",
    "cofunded_grant",
    "blended_finance",
    "equity",
    "loan",
    "prize",
    "investor_access",
    "accelerator",
    "training",
    "unknown",
]
OpportunityClass = Literal[
    "research_grant",
    "innovation_grant",
    "startup_funding",
    "spinout_funding",
    "deep_tech",
    "cascade_funding",
    "ecosystem_support",
    "other",
]


class InnovationOpportunityMetadata(BaseModel):
    """Innovation/start-up fields that remain evidence-gated like eligibility.

    These fields are intentionally separate from the core Opportunity model in the
    first migration tranche. Adapters can populate them only from authoritative
    programme/call evidence; absence remains unknown rather than being inferred.
    """

    opportunity_class: OpportunityClass | None = None
    venture_stages: list[str] = Field(default_factory=list)
    spinout_route: bool | None = None
    startup_age_limit_years: float | None = Field(default=None, ge=0)
    company_country_requirements: list[str] = Field(default_factory=list)
    cross_border_required: bool | None = None
    women_led_target: bool | None = None
    cofunding_rate_percent: float | None = Field(default=None, ge=0, le=100)
    funding_instrument: FundingInstrument = "unknown"
    programme_family: str | None = None
    dedupe_parent: str | None = None
    trl_min: int | None = Field(default=None, ge=1, le=9)
    trl_max: int | None = Field(default=None, ge=1, le=9)

    @model_validator(mode="after")
    def validate_ranges(self) -> "InnovationOpportunityMetadata":
        if self.trl_min is not None and self.trl_max is not None and self.trl_min > self.trl_max:
            raise ValueError("trl_min cannot exceed trl_max")
        return self


class InnovationProgramme(BaseModel):
    id: str
    name: str
    operator: str
    primary_url: HttpUrl
    programme_class: ProgrammeClass
    priority: Priority
    geography: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    venture_stages: list[str] = Field(default_factory=list)
    trl_min: int | None = Field(default=None, ge=1, le=9)
    trl_max: int | None = Field(default=None, ge=1, le=9)
    spinout_route: bool = False
    cross_border_required: bool | None = None
    women_led_target: bool = False
    dedupe_parent: str | None = None
    global_majority_relevance: GlobalMajorityRelevance
    notes: str | None = None

    @model_validator(mode="after")
    def validate_semantics(self) -> "InnovationProgramme":
        if self.trl_min is not None and self.trl_max is not None and self.trl_min > self.trl_max:
            raise ValueError("trl_min cannot exceed trl_max")
        if self.programme_class in {"eu_programme_pipeline", "cascade_funding"} and not self.dedupe_parent:
            raise ValueError(f"{self.programme_class} requires dedupe_parent")
        if self.programme_class == "ecosystem_access" and self.dedupe_parent:
            raise ValueError("ecosystem access records must not masquerade as deduped grant calls")
        return self

    @property
    def can_publish_as_grant_without_reclassification(self) -> bool:
        """Whether the programme class is intrinsically a funding route.

        This does not assert that a call is open or that an applicant is eligible.
        It only prevents meta/ecosystem entries from being represented as grants.
        """
        return self.programme_class in {
            "direct_funding",
            "eu_programme_pipeline",
            "cascade_funding",
        }


def load_innovation_programmes(
    path: str | Path = "config/innovation_programmes.yaml",
) -> tuple[dict, list[InnovationProgramme]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    policy = raw.get("policy", {})
    programmes = [InnovationProgramme.model_validate(item) for item in raw.get("programmes", [])]
    ids = [item.id for item in programmes]
    if len(ids) != len(set(ids)):
        raise ValueError("innovation programme ids must be unique")
    return policy, programmes


def programme_index(programmes: list[InnovationProgramme]) -> dict[str, InnovationProgramme]:
    return {item.id: item for item in programmes}
