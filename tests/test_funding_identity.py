from datetime import datetime, timedelta, timezone

from observatory.funding_identity import group_duplicates, stable_identity_key, stable_scheme_family_key
from observatory.funding_models import FundingDeadline, Opportunity


def base_opportunity(**overrides):
    data = dict(
        source_id="test",
        title="Global Health Research Call 2026 Round 1",
        funder="Example Foundation",
        programme="Global Health Programme",
        primary_url="https://example.org/call",
        global_majority_access="unclear",
    )
    data.update(overrides)
    return Opportunity(**data)


def test_next_actionable_deadline_uses_earliest_application_stage():
    now = datetime(2026, 8, 22, tzinfo=timezone.utc)
    opp = base_opportunity(
        closing_at=now + timedelta(days=90),
        deadlines=[
            FundingDeadline(stage="full_application", due_at=now + timedelta(days=90), label="Full"),
            FundingDeadline(stage="expression_of_interest", due_at=now + timedelta(days=20), label="EOI"),
            FundingDeadline(stage="interview", due_at=now + timedelta(days=110), label="Interview"),
        ],
    )
    assert opp.next_actionable_deadline(now) == now + timedelta(days=20)


def test_deadlines_must_be_timezone_aware():
    try:
        FundingDeadline(stage="full_application", due_at=datetime(2026, 9, 1))
    except ValueError:
        return
    raise AssertionError("naive deadlines must be rejected")


def test_recurring_rounds_are_distinct_opportunities_but_one_scheme_family():
    first = base_opportunity(title="Global Health Research Call 2026 Round 1")
    second = base_opportunity(title="Global Health Research Call 2027 Round 2", primary_url="https://example.org/call-2")
    assert stable_identity_key(first) != stable_identity_key(second)
    assert stable_scheme_family_key(first) == stable_scheme_family_key(second)


def test_external_ids_remain_distinct_even_with_same_title():
    one = base_opportunity(external_id="ABC-001")
    two = base_opportunity(external_id="ABC-002", primary_url="https://example.org/call-2")
    assert stable_identity_key(one) != stable_identity_key(two)


def test_same_nih_foa_merges_across_nih_and_fogarty():
    nih = base_opportunity(source_id="nih", external_id="RFA-TW-26-001", funder="NIH")
    fogarty = base_opportunity(source_id="fogarty", external_id="RFA-TW-26-001", funder="Fogarty", primary_url="https://example.org/fic")
    assert stable_identity_key(nih) == stable_identity_key(fogarty)


def test_duplicate_grouping_merges_true_duplicates_not_distinct_rounds():
    a = base_opportunity(title="Global Health Research Call 2026 Round 1")
    b = base_opportunity(title="Global Health Research Call 2027 Round 2", primary_url="https://example.org/call-2")
    assert group_duplicates([a, b]) == ()
    c = base_opportunity(title="Global Health Research Call 2026 Round 1", source_id="mirror")
    groups = group_duplicates([a, c])
    assert len(groups) == 1
    assert len(groups[0].records) == 2
