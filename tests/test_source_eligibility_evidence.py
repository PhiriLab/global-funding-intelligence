from observatory.source_eligibility_evidence import summarise_eligibility_evidence


def test_ukri_evidence_is_preserved_without_becoming_eligibility_verdict():
    summary = summarise_eligibility_evidence(
        "ukri_funding_finder",
        (
            "You must be based at a UK research organisation eligible for UKRI funding.",
            "International project co-leads may be included where the opportunity permits.",
        ),
    )
    assert summary.application_access == "open_or_unspecified"
    assert "UK research-organisation requirement stated" in summary.note
    assert "international participation wording stated" in summary.note
    assert "no eligibility verdict inferred" in summary.note


def test_invitation_only_is_explicitly_flagged_but_not_converted_to_country_route():
    summary = summarise_eligibility_evidence(
        "ukri_funding_finder",
        ("This opportunity is by invitation only.",),
    )
    assert summary.application_access == "invite_only"
    assert "invitation-only" in summary.note


def test_nihr_evidence_recognises_contracting_and_lmic_language():
    summary = summarise_eligibility_evidence(
        "nihr_funding",
        (
            "The lead applicant must identify the contracting organisation.",
            "Applications involving LMIC partners must describe equitable partnerships.",
        ),
    )
    assert "contracting-organisation requirement stated" in summary.note
    assert "lead/co-applicant role wording stated" in summary.note
    assert "LMIC participation wording stated" in summary.note
    assert "partner wording stated" in summary.note


def test_wellcome_evidence_recognises_host_and_administering_organisation_terms():
    summary = summarise_eligibility_evidence(
        "wellcome_funding",
        (
            "Your administering organisation must agree to administer the award.",
            "You must have an eligible host organisation.",
        ),
    )
    assert "administering-organisation requirement stated" in summary.note
    assert "host-organisation requirement stated" in summary.note


def test_no_evidence_stays_empty():
    summary = summarise_eligibility_evidence("wellcome_funding", ())
    assert summary.application_access == "open_or_unspecified"
    assert summary.evidence == ()
    assert summary.note is None
