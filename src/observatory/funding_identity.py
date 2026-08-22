from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse

from .funding_models import Opportunity


def _slug(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _family_slug(value: str | None) -> str:
    text = _slug(value)
    text = re.sub(r"(?:^|-)(20\d{2}|19\d{2})(?:-|$)", "-", text)
    text = re.sub(r"(?:^|-)(round|call|cycle|wave)-?\d+(?:-|$)", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def _external_namespace(opportunity: Opportunity) -> str:
    source = opportunity.source_id.lower()
    external = (opportunity.external_id or "").strip().upper()
    if source in {"nih", "nih_grants", "fogarty"} and re.match(r"^(RFA|PA|PAR|PAS|NOT)-[A-Z0-9-]+$", external):
        return "nih"
    return source


def stable_identity_key(opportunity: Opportunity) -> str:
    if opportunity.external_id:
        seed = f"{_external_namespace(opportunity)}|external|{opportunity.external_id.strip().lower()}"
    else:
        parsed = urlparse(str(opportunity.primary_url))
        canonical_location = f"{(parsed.hostname or '').lower()}{parsed.path.rstrip('/').lower()}"
        seed = "|".join([_slug(opportunity.funder), _slug(opportunity.programme), _slug(opportunity.title), canonical_location])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"gfi:{digest}"


def stable_scheme_family_key(opportunity: Opportunity) -> str:
    seed = "|".join([_family_slug(opportunity.funder), _family_slug(opportunity.programme), _family_slug(opportunity.title)])
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return f"gfi-family:{digest}"


@dataclass(frozen=True)
class DedupGroup:
    identity_key: str
    records: tuple[Opportunity, ...]


def group_duplicates(opportunities: list[Opportunity]) -> tuple[DedupGroup, ...]:
    groups: dict[str, list[Opportunity]] = {}
    for opportunity in opportunities:
        key = opportunity.identity_key or stable_identity_key(opportunity)
        groups.setdefault(key, []).append(opportunity)
    return tuple(DedupGroup(identity_key=key, records=tuple(records)) for key, records in sorted(groups.items()) if len(records) > 1)
