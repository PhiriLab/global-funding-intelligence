from observatory.structured_eligibility import extract_structured_eligibility


def test_ukri_labelled_fields_populate_machine_routes():
    result = extract_structured_eligibility(
        "ukri_funding_finder",
        [
            "Eligible organisations: university, research institute",
            "Lead applicant countries: GB",
            "Partner countries: ZA, KE",
            "Consortium required: yes",
            "Lead applicant location: United Kingdom",
        ],
    )
    assert result.applicant_types == ("university", "research institute")
    assert result.lead_countries == ("GB",)
    assert result.partner_countries == ("ZA", "KE")
    assert result.consortium_required is True
    assert result.lead_location_rule == "United Kingdom"
    assert result.global_majority_access == "direct"


def test_nihr_labelled_lmic_and_oda_fields_are_structured():
    result = extract_structured_eligibility(
        "nihr_funding",
        [
            "Eligible income groups: LIC, LMIC",
            "ODA only: yes",
            "Local partner required: required",
            "LMIC or equity requirement: equitable partnership required",
        ],
    )
    assert result.eligible_income_groups == ("LIC", "LMIC")
    assert result.oda_only is True
    assert result.local_partner_required is True
    assert result.equity_or_lmic_requirement == "equitable partnership required"
    assert result.global_majority_access == "direct"


def test_wellcome_labelled_host_fields_are_structured():
    result = extract_structured_eligibility(
        "wellcome_funding",
        [
            "Administering organisation types: university, research institute",
            "Host organisation countries: ZA",
        ],
    )
    assert result.applicant_types == ("university", "research institute")
    assert result.lead_countries == ("ZA",)
    assert result.global_majority_access == "direct"


def test_narrative_eligibility_text_is_not_promoted():
    result = extract_structured_eligibility(
        "ukri_funding_finder",
        [
            "You must be based at a UK research organisation eligible for UKRI funding.",
            "International project co-leads may be included.",
        ],
    )
    assert result.applicant_types == ()
    assert result.eligible_countries == ()
    assert result.lead_countries == ()
    assert result.partner_countries == ()
    assert result.global_majority_access == "unclear"


def test_non_iso_country_labels_fail_closed():
    result = extract_structured_eligibility(
        "ukri_funding_finder",
        ["Eligible countries: United Kingdom, South Africa"],
    )
    assert result.eligible_countries == ()
    assert "ignored non-ISO structured field: eligible_countries" in result.warnings
