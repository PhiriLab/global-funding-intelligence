from pathlib import Path

import pytest

from observatory.funding_extract import ExtractedFundingRecord
from observatory.public_funding_export import (
    SourceState,
    export_link_only,
    export_structured_record,
    resolve_source_state,
)


def test_structured_export_never_computes_eligibility():
    record = ExtractedFundingRecord(
        source_id="idrc",
        primary_url="https://idrc-crdi.ca/en/funding/example",
        title="Example call",
        funder="IDRC",
        currency="CAD",
        max_award=300_000,
        eligibility_evidence=("Principal applicant must be based in an eligible country",),
    )
    public = export_structured_record(record, source_checked_at="2026-08-22T19:00:00Z")
    assert public.source_state is SourceState.structured_beta
    assert public.eligibility == "Not determined — verify at source"
    assert "eligibility_evidence" not in public.model_dump()


def test_registry_is_authoritative_for_source_state():
    assert resolve_source_state("idrc") is SourceState.structured_beta
    assert resolve_source_state("cepi") is SourceState.partial


def test_partial_source_cannot_be_promoted_to_structured_export():
    record = ExtractedFundingRecord(
        source_id="cepi",
        primary_url="https://cepi.net/calls-for-proposals",
        title="CEPI calls",
        funder="CEPI",
        max_award=1_000_000,
    )
    with pytest.raises(ValueError, match="partial"):
        export_structured_record(record, source_checked_at="2026-08-22T19:00:00Z")


def test_non_structured_sources_are_link_only_with_registry_state():
    item = export_link_only(
        source_id="cepi",
        funder="CEPI",
        title="CEPI calls for proposals",
        primary_url="https://cepi.net/calls-for-proposals",
        source_checked_at="2026-08-22T19:00:00Z",
    )
    assert item.source_state is SourceState.partial
    assert item.max_award is None and item.deadline is None


def test_structured_source_cannot_use_link_only_path():
    with pytest.raises(ValueError, match="structured beta"):
        export_link_only(
            source_id="idrc",
            funder="IDRC",
            title="IDRC funding",
            primary_url="https://idrc-crdi.ca/en/funding",
            source_checked_at="2026-08-22T19:00:00Z",
        )


def test_unknown_source_fails_closed():
    with pytest.raises(ValueError, match="trusted ingestion registry"):
        export_link_only(
            source_id="unreviewed_source",
            funder="Unknown",
            title="Unknown funding",
            primary_url="https://example.org/funding",
            source_checked_at="2026-08-22T19:00:00Z",
        )


def _public_allowlist() -> set[str]:
    public_manifest = Path("config/public_export_allowlist.txt")
    assert public_manifest.exists()
    return {
        line.strip()
        for line in public_manifest.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_public_tree_denylist_excludes_private_observatory_content():
    denied = {"config/projects.yaml", "digests", "HANDOFF.md", "src/observatory/scout.py", "scripts/run_scout.py"}
    allowed = _public_allowlist()
    for path in denied:
        assert path not in allowed
    assert all(not entry.startswith("digests/") for entry in allowed)


def test_live_web_release_is_declared_in_public_allowlist():
    allowed = _public_allowlist()
    required = {
        "docs/EMBED.md",
        "web/index.html",
        "web/styles.css",
        "web/app.js",
        "web/wix-bundle.html",
        "tests/test_web_interface.py",
        ".github/workflows/pages.yml",
    }
    assert required <= allowed
