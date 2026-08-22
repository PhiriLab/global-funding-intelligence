from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CountryClassification:
    code: str
    name: str
    income_group: str | None
    oda_eligible: bool | None


def load_country_classifications(path: str | Path = "config/country_classification.yaml") -> dict[str, CountryClassification]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    countries = raw.get("countries", {})
    result: dict[str, CountryClassification] = {}
    for code, item in countries.items():
        iso = str(code).strip().upper()
        if len(iso) != 2 or not iso.isalpha():
            raise ValueError(f"invalid ISO-3166 alpha-2 country code: {code}")
        result[iso] = CountryClassification(code=iso, name=str(item.get("name", iso)), income_group=item.get("income_group"), oda_eligible=item.get("oda_eligible"))
    return result


def classify_country(code: str, path: str | Path = "config/country_classification.yaml") -> CountryClassification | None:
    return load_country_classifications(path).get(code.strip().upper())


def enrich_applicant_profile(profile, path: str | Path = "config/country_classification.yaml"):
    classification = classify_country(profile.country, path)
    if classification is None:
        return profile
    updates = {}
    if getattr(profile, "income_group", None) is None:
        updates["income_group"] = classification.income_group
    if getattr(profile, "oda_eligible", None) is None:
        updates["oda_eligible"] = classification.oda_eligible
    return profile.model_copy(update=updates) if updates else profile
