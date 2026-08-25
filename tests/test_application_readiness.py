from pathlib import Path

WEB = Path('web')
READINESS_JS = (WEB / 'application-readiness.js').read_text(encoding='utf-8')
READINESS_CSS = (WEB / 'application-readiness.css').read_text(encoding='utf-8')
JOURNEY_JS = (WEB / 'application-journey.js').read_text(encoding='utf-8')


def test_readiness_module_is_loaded_after_application_journey():
    # Readiness must load exactly once, ordered after application-journey. This is
    # done by index.html's script order — NOT by a dynamic injector in
    # application-journey.js, which caused a `readinessStyle` double-declaration.
    index = (WEB / 'index.html').read_text(encoding='utf-8')
    assert index.count('src="application-readiness.js"') == 1
    assert index.index('src="application-journey.js"') < index.index('src="application-readiness.js"')
    assert "readinessScript" not in JOURNEY_JS
    assert (WEB / 'application-readiness.js').is_file()
    assert (WEB / 'application-readiness.css').is_file()


def test_readiness_is_evidence_first_and_never_guesses_unknowns():
    for marker in (
        "Actionable deadline is not structured",
        "Applicant eligibility evidence is incomplete in the structured source",
        "Consortium or local-partner requirements are not fully structured",
        "state = 'verify'",
        "state = 'blocked'",
        "state = 'ready'",
    ):
        assert marker in READINESS_JS
    assert "Eligibility verified at the primary source" in READINESS_JS
    assert "Consortium / partner requirements verified at source" in READINESS_JS
    assert "It is not a funder eligibility determination" in READINESS_JS


def test_expired_or_closed_calls_are_blocked():
    assert "days < 0" in READINESS_JS
    assert "The verified deadline has passed" in READINESS_JS
    assert "opportunity?.lifecycle === 'closed'" in READINESS_JS
    assert "blockers.length" in READINESS_JS


def test_deadline_intelligence_has_urgent_soon_and_workable_bands():
    assert "days <= 7" in READINESS_JS
    assert "days <= 21" in READINESS_JS
    for state in ("urgent", "soon", "workable", "expired", "unknown"):
        assert f"state:'{state}'" in READINESS_JS
    assert "Verified deadline override" in READINESS_JS
    assert "data-manual-deadline" in READINESS_JS


def test_stage_checklist_is_progressive_not_globally_over_required():
    assert "journey.stage === 'partner_building'" in READINESS_JS
    assert "opportunity?.consortium_required === true" in READINESS_JS
    assert "opportunity?.local_partner_required === true" in READINESS_JS
    for field in (
        'guidance_reviewed', 'eligibility_verified', 'requirements_verified',
        'internal_go_no_go', 'consortium_ready', 'local_partner_ready',
        'narrative_ready', 'budget_ready', 'documents_ready',
        'internal_approval_ready', 'portal_ready'
    ):
        assert field in READINESS_JS


def test_readiness_remains_local_and_does_not_add_identity_or_proposal_collection():
    assert "saveJourneys()" in READINESS_JS
    assert "/rest/v1/" not in READINESS_JS
    for forbidden in ('name', 'email', 'proposal_text', 'reviewer_comments', 'collaborator_details', 'visitor_id', 'session_id', 'ip_address'):
        assert f"'{forbidden}'" not in READINESS_JS


def test_readiness_styles_include_all_states():
    for selector in (
        '.readiness-state.ready', '.readiness-state.verify', '.readiness-state.action_needed',
        '.readiness-state.blocked', '.readiness-state.submitted', '.deadline-chip.urgent',
        '.deadline-chip.expired', '.manual-deadline'
    ):
        assert selector in READINESS_CSS
