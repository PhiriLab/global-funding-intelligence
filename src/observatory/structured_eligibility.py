from __future__ import annotations

from dataclasses import dataclass, field

from .country_data import classify_country


@dataclass(frozen=True)
class StructuredEligibility:
    applicant_types: tuple[str, ...] = ()
    eligible_countries: tuple[str, ...] = ()
    excluded_countries: tuple[str, ...] = ()
    lead_countries: tuple[str, ...] = ()
    partner_countries: tuple[str, ...] = ()
    eligible_income_groups: tuple[str, ...] = ()
    oda_only: bool | None = None
    consortium_required: bool | None = None
    local_partner_required: bool | None = None
    lead_location_rule: str | None = None
    equity_or_lmic_requirement: str | None = None
    global_majority_access: str = "unclear"
    warnings: tuple[str, ...] = field(default_factory=tuple)


_SOURCE_LABELS = {
    "ukri_funding_finder": {
        "applicant_types": ("Eligible organisations", "Eligible organization types", "Eligible organisation types"),
        "eligible_countries": ("Eligible countries",),
        "excluded_countries": ("Excluded countries",),
        "lead_countries": ("Lead applicant countries", "Project lead countries"),
        "partner_countries": ("Partner countries", "Project partner countries"),
        "consortium_required": ("Consortium required",),
        "lead_location_rule": ("Lead applicant location", "Project lead location"),
    },
    "nihr_funding": {
        "applicant_types": ("Eligible organisations", "Eligible organisation types", "Contracting organisation types"),
        "eligible_countries": ("Eligible countries",),
        "lead_countries": ("Lead applicant countries",),
        "partner_countries": ("Partner countries",),
        "eligible_income_groups": ("Eligible income groups",),
        "oda_only": ("ODA eligible only", "ODA only"),
        "consortium_required": ("Consortium required",),
        "local_partner_required": ("Local partner required",),
        "lead_location_rule": ("Lead applicant location",),
        "equity_or_lmic_requirement": ("LMIC or equity requirement", "Equity requirement"),
    },
    "wellcome_funding": {
        "applicant_types": ("Eligible organisations", "Eligible organisation types", "Administering organisation types"),
        "eligible_countries": ("Eligible countries",),
        "lead_countries": ("Lead applicant countries", "Host organisation countries"),
        "partner_countries": ("Partner countries",),
        "eligible_income_groups": ("Eligible income groups",),
        "consortium_required": ("Consortium required",),
        "local_partner_required": ("Local partner required",),
        "lead_location_rule": ("Host organisation location", "Lead applicant location"),
        "equity_or_lmic_requirement": ("LMIC or equity requirement", "Equity requirement"),
    },
}


def _value_after_label(lines: list[str], labels: tuple[str, ...]) -> str | None:
    lowered = [(line.strip(), line.strip().lower()) for line in lines]
    for label in labels:
        target = label.lower().rstrip(":")
        for idx, (raw, low) in enumerate(lowered):
            if low in {target, target + ":"}:
                return lowered[idx + 1][0] if idx + 1 < len(lowered) else None
            prefix = target + ":"
            if low.startswith(prefix):
                value = raw[len(prefix):].strip()
                return value or (lowered[idx + 1][0] if idx + 1 < len(lowered) else None)
    return None


def _csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    parts = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    return tuple(dict.fromkeys(parts))


def _country_codes(value: str | None) -> tuple[str, ...]:
    codes = tuple(item.upper() for item in _csv(value))
    return codes if all(len(item) == 2 and item.isalpha() for item in codes) else ()


def _bool(value: str | None) -> bool | None:
    if not value:
        return None
    low = value.strip().lower()
    if low in {"yes", "required", "true"}:
        return True
    if low in {"no", "not required", "false"}:
        return False
    return None


def _is_global_majority_country(code: str) -> bool | None:
    classification = classify_country(code)
    if classification is None:
        return None
    if classification.oda_eligible is True:
        return True
    if classification.income_group in {"LIC", "LMIC", "UMIC"}:
        return True
    if classification.oda_eligible is False and classification.income_group == "HIC":
        return False
    return None


def _global_majority_route(
    eligible_countries: tuple[str, ...],
    lead_countries: tuple[str, ...],
    partner_countries: tuple[str, ...],
    eligible_income_groups: tuple[str, ...],
) -> str:
    if any(group in {"LIC", "LMIC", "UMIC"} for group in eligible_income_groups):
        return "direct"
    direct_codes = lead_countries or eligible_countries
    direct_states = [_is_global_majority_country(code) for code in direct_codes]
    if any(state is True for state in direct_states):
        return "direct"
    partner_states = [_is_global_majority_country(code) for code in partner_countries]
    if any(state is True for state in partner_states) and direct_codes:
        return "partner_only"
    return "unclear"


def extract_structured_eligibility(source_id: str, lines: list[str]) -> StructuredEligibility:
    labels = _SOURCE_LABELS.get(source_id)
    if not labels:
        return StructuredEligibility()

    raw = {key: _value_after_label(lines, label_set) for key, label_set in labels.items()}
    warnings: list[str] = []
    country_fields = ("eligible_countries", "excluded_countries", "lead_countries", "partner_countries")
    countries = {key: _country_codes(raw.get(key)) for key in country_fields}
    for key in country_fields:
        if raw.get(key) and not countries[key]:
            warnings.append(f"ignored non-ISO structured field: {key}")

    income = tuple(item.upper() for item in _csv(raw.get("eligible_income_groups")))
    allowed_income = tuple(item for item in income if item in {"LIC", "LMIC", "UMIC", "HIC"})
    if income and len(income) != len(allowed_income):
        warnings.append("ignored unsupported income-group values")

    gm = _global_majority_route(
        countries["eligible_countries"],
        countries["lead_countries"],
        countries["partner_countries"],
        allowed_income,
    )

    return StructuredEligibility(
        applicant_types=_csv(raw.get("applicant_types")),
        eligible_countries=countries["eligible_countries"],
        excluded_countries=countries["excluded_countries"],
        lead_countries=countries["lead_countries"],
        partner_countries=countries["partner_countries"],
        eligible_income_groups=allowed_income,
        oda_only=_bool(raw.get("oda_only")),
        consortium_required=_bool(raw.get("consortium_required")),
        local_partner_required=_bool(raw.get("local_partner_required")),
        lead_location_rule=raw.get("lead_location_rule"),
        equity_or_lmic_requirement=raw.get("equity_or_lmic_requirement"),
        global_majority_access=gm,
        warnings=tuple(warnings),
    )
