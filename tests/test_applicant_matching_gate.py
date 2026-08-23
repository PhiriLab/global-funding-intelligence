from datetime import datetime, timedelta, timezone

from observatory.funding_models import ApplicantProfile, Opportunity, OpportunityStatus, score_opportunity


NOW = datetime(2026, 8, 23, 3, 0, tzinfo=timezone.utc)


def applicant(**overrides):
    data = dict(
        country="ZA",
        organisation_type="university",
        sectors=["mental health"],
        stages=["clinical research"],
        career_stage="senior",
        years_since_phd=12,
        trl=5,
        can_form_consortium=True,
        has_required_local_partner=True,
    )
    data.update(overrides)
    return ApplicantProfile(**data)


def opportunity(**overrides):
    data = dict(
        source_id="idrc",
        external_id="CALL-1",
        title="Global mental health research call",
        funder="IDRC",
        primary_url="https://idrc-crdi.ca/en/funding/example",
        status=OpportunityStatus.open,
        lead_countries=["ZA"],
        applicant_types=["university"],
        sectors=["mental health"],
        stages=["clinical research"],
        global_majority_access="direct",
        closing_at=NOW + timedelta(days=60),
        max_award=500_000,
        source_checked_at=NOW,
    )
    data.update(overrides)
    return Opportunity(**data)


def test_explicit_country_exclusion_fails_gate_and_skips():
    result = score_opportunity(opportunity(lead_countries=[], excluded_countries=["ZA"]), applicant(), now=NOW)
    assert result.eligibility_gate == "fail"
    assert result.participation_route == "ineligible"
    assert result.decision == "skip"
    assert "country eligibility" in result.blockers


def test_partner_only_country_returns_partner_decision_when_other_gates_pass():
    result = score_opportunity(
        opportunity(lead_countries=["GB"], partner_countries=["ZA"], global_majority_access="partner_only"),
        applicant(),
        now=NOW,
    )
    assert result.eligibility_gate == "pass"
    assert result.participation_route == "partner"
    assert result.decision == "partner"


def test_missing_country_and_organisation_evidence_remains_uncertain_and_verify():
    result = score_opportunity(
        opportunity(lead_countries=[], applicant_types=[], global_majority_access="unclear"),
        applicant(),
        now=NOW,
    )
    assert result.eligibility_gate == "uncertain"
    assert result.participation_route == "unknown"
    assert result.decision == "verify"
    assert set(result.unknowns) == {"country eligibility", "organisation type"}


def test_unstated_optional_requirements_do_not_become_eligibility_unknowns():
    result = score_opportunity(
        opportunity(consortium_required=None, local_partner_required=None),
        applicant(can_form_consortium=False, has_required_local_partner=False),
        now=NOW,
    )
    assert "consortium requirement" not in result.unknowns
    assert "local partner requirement" not in result.unknowns
    assert result.eligibility_gate == "pass"


def test_explicit_required_consortium_is_a_blocker_when_applicant_cannot_form_one():
    result = score_opportunity(opportunity(consortium_required=True), applicant(can_form_consortium=False), now=NOW)
    assert result.eligibility_gate == "fail"
    assert result.decision == "skip"
    assert "consortium requirement" in result.blockers


def test_missing_thematic_fields_are_fit_unknowns_not_positive_fit_evidence():
    result = score_opportunity(opportunity(sectors=[], stages=[], trl_min=None, trl_max=None), applicant(), now=NOW)
    assert result.strategic_fit == 50
    assert "opportunity sectors not structured" in result.fit_unknowns
    assert "opportunity stages not structured" in result.fit_unknowns
    assert "sector match" not in result.reasons


def test_closed_or_expired_call_always_skips_even_if_eligibility_passes():
    result = score_opportunity(
        opportunity(status=OpportunityStatus.open, closing_at=NOW - timedelta(hours=1)),
        applicant(),
        now=NOW,
    )
    assert result.decision == "skip"
    assert "opportunity closed or deadline passed" in result.blockers


def test_missing_deadline_for_open_call_prevents_apply_recommendation():
    result = score_opportunity(opportunity(closing_at=None, rolling=False), applicant(), now=NOW)
    assert result.eligibility_gate == "pass"
    assert result.decision == "verify"
    assert "actionable deadline not verified" in result.fit_unknowns


def test_case_insensitive_organisation_type_match():
    result = score_opportunity(opportunity(applicant_types=["University"]), applicant(organisation_type="university"), now=NOW)
    assert result.eligibility_gate == "pass"
    assert "organisation type" not in result.blockers
