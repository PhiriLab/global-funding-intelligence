from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


ApplicationAccess = Literal["open_or_unspecified", "invite_only"]


@dataclass(frozen=True)
class EligibilityEvidenceSummary:
    application_access: ApplicationAccess
    evidence: tuple[str, ...]
    note: str | None


_SOURCE_TERMS: dict[str, tuple[tuple[str, str], ...]] = {
    "ukri_funding_finder": (
        (r"\bUK research organisation\b", "UK research-organisation requirement stated"),
        (r"\bmust be based\b", "applicant-location requirement stated"),
        (r"\binternational(?:\s+\w+){0,3}\s+co-?leads?\b|\binternational(?:\s+\w+){0,3}\s+partners?\b", "international participation wording stated"),
        (r"\bproject leads?\b|\bproject co-?leads?\b", "lead/co-lead role wording stated"),
    ),
    "nihr_funding": (
        (r"\bcontracting organisation\b", "contracting-organisation requirement stated"),
        (r"\blead applicant\b|\bco-applicant\b", "lead/co-applicant role wording stated"),
        (r"\bNHS\b|\bhealth and care\b", "UK health/care organisation wording stated"),
        (r"\bLMIC\b|low[- ]and middle[- ]income", "LMIC participation wording stated"),
    ),
    "wellcome_funding": (
        (r"\badministering organisation\b", "administering-organisation requirement stated"),
        (r"\bhost organisation\b", "host-organisation requirement stated"),
        (r"\beligible organisation\b|\borganisation must\b", "organisation eligibility wording stated"),
        (r"\blow[- ]and middle[- ]income\b|\bLMIC\b", "LMIC participation wording stated"),
    ),
}


def summarise_eligibility_evidence(source_id: str, evidence: tuple[str, ...]) -> EligibilityEvidenceSummary:
    cleaned = tuple(dict.fromkeys(line.strip() for line in evidence if line and line.strip()))
    if not cleaned:
        return EligibilityEvidenceSummary("open_or_unspecified", (), None)

    combined = "\n".join(cleaned)
    invite_only = bool(re.search(r"\bby invitation only\b|\binvite only\b|\binvitation[- ]only\b", combined, flags=re.I))

    signals: list[str] = []
    for pattern, label in _SOURCE_TERMS.get(source_id, ()):
        if re.search(pattern, combined, flags=re.I):
            signals.append(label)
    if re.search(r"\bconsortium\b", combined, flags=re.I):
        signals.append("consortium wording stated")
    if re.search(r"\bODA\b", combined, flags=re.I):
        signals.append("ODA wording stated")
    if re.search(r"\bpartners?\b", combined, flags=re.I):
        signals.append("partner wording stated")

    signals = list(dict.fromkeys(signals))
    access = "invite_only" if invite_only else "open_or_unspecified"
    prefix = "Primary source explicitly marks this opportunity invitation-only." if invite_only else "Primary-source eligibility wording captured; no eligibility verdict inferred."
    if signals:
        prefix += " Signals: " + "; ".join(signals[:6]) + "."

    snippets = " | ".join(cleaned[:3])
    note = f"{prefix} Evidence: {snippets}"
    return EligibilityEvidenceSummary(access, cleaned[:12], note)
