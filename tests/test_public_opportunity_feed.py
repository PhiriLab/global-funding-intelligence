from datetime import datetime, timezone

import pytest

from observatory.funding_models import Opportunity, OpportunityStatus
from observatory.public_opportunity_feed import OpportunityLifecycle, classify_lifecycle, to_public_opportunity
from observatory.sources.eu_funding_tenders import is_edctp3_record, normalise_edctp3_records, normalise_eu_record


NOW = datetime(2026, 8, 23, 1, 0, tzinfo=timezone.utc)


def eu_record(**overrides):
    record = {
        "identifier": "HORIZON-JU-GH-EDCTP3-2026-01-01",
        "title": "Global Health EDCTP3 clinical research topic",
        "frameworkProgrammeDescription": "Horizon Europe / Global Health EDCTP3",
        "statusDescription": "Open",
        "openingDate": "2026-07-01T00:00:00Z",
        "deadlineDate": "2026-09-15T17:00:00Z",
        "ccm2Id": "123456",
    }
    record.update(overrides)
    return record


def test_edctp3_is_a_deterministic_subset_of_eu_records():
    assert is_edctp3_record(eu_record()) is True
    assert is_edctp3_record(eu_record(identifier="HORIZON-HLTH-2026-01", title="General health topic", frameworkProgrammeDescription="Horizon Europe")) is False
    records = normalise_edctp3_records([eu_record(), eu_record(identifier="HORIZON-HLTH-2026-01", title="General health topic", frameworkProgrammeDescription="Horizon Europe")])
    assert len(records) == 1
    assert records[0].source_id == "eu_funding_tenders"


def test_eu_record_normalises_primary_fields_without_inventing_eligibility():
    opportunity = normalise_eu_record(eu_record())
    assert opportunity.external_id == "HORIZON-JU-GH-EDCTP3-2026-01-01"
    assert opportunity.status == OpportunityStatus.open
    assert opportunity.closing_at == datetime(2026, 9, 15, 17, 0, tzinfo=timezone.utc)
    assert opportunity.global_majority_access == "unclear"
    assert opportunity.eligible_countries == []
    assert "topic-details/HORIZON-JU-GH-EDCTP3-2026-01-01" in str(opportunity.primary_url)


def test_public_feed_uses_trusted_registry_state_and_keeps_eligibility_unknown():
    public = to_public_opportunity(normalise_eu_record(eu_record()), now=NOW)
    assert public.source_state.value == "structured_beta"
    assert public.eligibility == "Not determined — verify at source"
    assert public.lifecycle == OpportunityLifecycle.closing_soon
    assert any("Global Majority" in warning for warning in public.warnings)


def test_lifecycle_is_deterministic():
    base = dict(source_id="eu_funding_tenders", title="x", funder="European Commission", primary_url="https://example.org/call", source_checked_at=NOW)
    assert classify_lifecycle(Opportunity(**base, status=OpportunityStatus.open, closing_at=datetime(2026, 12, 1, tzinfo=timezone.utc)), now=NOW) == OpportunityLifecycle.open
    assert classify_lifecycle(Opportunity(**base, status=OpportunityStatus.open, closing_at=datetime(2026, 8, 30, tzinfo=timezone.utc)), now=NOW) == OpportunityLifecycle.closing_soon
    assert classify_lifecycle(Opportunity(**base, status=OpportunityStatus.upcoming, opening_at=datetime(2026, 9, 1, tzinfo=timezone.utc)), now=NOW) == OpportunityLifecycle.upcoming
    assert classify_lifecycle(Opportunity(**base, status=OpportunityStatus.rolling, rolling=True), now=NOW) == OpportunityLifecycle.rolling
    assert classify_lifecycle(Opportunity(**base, status=OpportunityStatus.open, closing_at=datetime(2026, 8, 1, tzinfo=timezone.utc)), now=NOW) == OpportunityLifecycle.closed


def test_non_structured_source_still_cannot_publish_opportunity_fields():
    opportunity = Opportunity(source_id="cepi", title="CEPI call", funder="CEPI", primary_url="https://cepi.net/calls-for-proposals", status=OpportunityStatus.open, source_checked_at=NOW)
    with pytest.raises(ValueError, match="only trusted structured sources"):
        to_public_opportunity(opportunity, now=NOW)
