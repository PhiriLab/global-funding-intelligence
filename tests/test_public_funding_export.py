from pathlib import Path

import pytest

from observatory.funding_extract import ExtractedFundingRecord
from observatory.public_funding_export import SourceState, export_link_only, export_structured_record


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
    public = export_structured_record(record, source_state=SourceState.structured_beta, source_checked_at="2026-08-22T19:00:00Z")
    assert public.eligibility == "Not determined — verify at source"
    assert "eligibility_evidence" not in public.model_dump()


def test_non_structured_sources_are_link_only():
    with pytest.raises(ValueError):
        export_structured_record(
            ExtractedFundingRecord(source_id="cepi", primary_url="https://cepi.net/calls-proposals", title="CEPI calls", funder="CEPI"),
            source_state=SourceState.partial,
            source_checked_at="2026-08-22T19:00:00Z",
        )
    item = export_link_only(funder="CEPI", title="CEPI calls for proposals", primary_url="https://cepi.net/calls-proposals", source_state=SourceState.partial, source_checked_at="2026-08-22T19:00:00Z")
    assert item.max_award is None and item.deadline is None


def test_source_state_is_validated_enum():
    with pytest.raises(ValueError):
        export_link_only(funder="Example", title="Example", primary_url="https://example.org/funding", source_state="live", source_checked_at="2026-08-22T19:00:00Z")  # type: ignore[arg-type]


def test_public_tree_denylist_excludes_private_observatory_content():
    denied = {"config/projects.yaml", "digests", "HANDOFF.md", "src/observatory/scout.py", "scripts/run_scout.py"}
    public_manifest = Path("config/public_export_allowlist.txt")
    assert public_manifest.exists()
    allowed = {line.strip() for line in public_manifest.read_text().splitlines() if line.strip() and not line.startswith("#")}
    for path in denied:
        assert path not in allowed
    assert all(not entry.startswith("digests/") for entry in allowed)
