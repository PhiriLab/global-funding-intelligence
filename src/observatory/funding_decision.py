from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .country_data import enrich_applicant_profile
from .funding_models import ApplicantProfile, FundingScore, Opportunity, score_opportunity


def evaluate_opportunity(
    opportunity: Opportunity,
    applicant: ApplicantProfile,
    *,
    country_data_path: str | Path = "config/country_classification.yaml",
    now: datetime | None = None,
) -> FundingScore:
    enriched = enrich_applicant_profile(applicant, country_data_path)
    return score_opportunity(opportunity, enriched, now=now)
