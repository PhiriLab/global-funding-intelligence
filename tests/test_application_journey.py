from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
JOURNEY_JS = (WEB / "application-journey.js").read_text(encoding="utf-8")
JOURNEY_CSS = (WEB / "application-journey.css").read_text(encoding="utf-8")
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
SQL = (ROOT / "db" / "application_journey_v1.sql").read_text(encoding="utf-8")


def test_application_journey_assets_are_loaded_after_opportunity_feed():
    assert (WEB / "application-journey.js").is_file()
    assert (WEB / "application-journey.css").is_file()
    assert 'src="opportunities.js"' in INDEX
    assert 'src="application-journey.js"' in INDEX
    assert INDEX.index('src="opportunities.js"') < INDEX.index('src="application-journey.js"')
    assert "application-journey.css" in JOURNEY_JS


def test_saved_portfolio_is_local_and_sharing_is_explicit_opt_in():
    assert "gfi-application-journeys-v1" in JOURNEY_JS
    assert "localStorage.getItem" in JOURNEY_JS
    assert "localStorage.setItem" in JOURNEY_JS
    assert "share_evaluation: false" in JOURNEY_JS
    assert "Share anonymous stage transitions with the GFI evaluation" in JOURNEY_JS
    assert "if (!journey.share_evaluation)" in JOURNEY_JS
    assert "Saved locally only." in JOURNEY_JS


def test_lifecycle_contains_expected_application_stages_and_user_declared_outcomes():
    for stage in (
        "saved", "eligibility_checked", "partner_building", "decision_to_apply",
        "drafting", "internal_review", "submitted", "interview_rebuttal",
        "pending", "awarded", "unsuccessful", "withdrawn", "not_disclosed",
    ):
        assert stage in JOURNEY_JS
        assert stage in SQL
    assert "outcomeFromStage" in JOURNEY_JS
    assert "journey.outcome = outcomeFromStage(journey.stage)" in JOURNEY_JS
    assert "inactivity" not in JOURNEY_JS.lower()


def test_journey_server_collection_is_append_only_and_contains_no_proposal_content():
    assert "/rest/v1/gfi_application_journey_events" in JOURNEY_JS
    assert "method: 'POST'" in JOURNEY_JS
    assert "method: 'GET'" not in JOURNEY_JS
    for forbidden in (
        "proposal_text", "reviewer_comments", "collaborator_name", "applicant_name",
        "email_address", "visitor_id", "session_id", "fingerprint", "ip_address",
    ):
        assert forbidden not in JOURNEY_JS
        assert forbidden not in SQL
    assert "no name, email, proposal text, collaborator details or reviewer comments" in JOURNEY_JS


def test_database_policy_is_insert_only_with_private_reporting_views():
    assert "enable row level security" in SQL.lower()
    assert "revoke all on public.gfi_application_journey_events from anon, authenticated" in SQL
    assert "grant insert on public.gfi_application_journey_events to anon, authenticated" in SQL
    assert "for insert" in SQL.lower()
    assert "for select" not in SQL.lower()
    assert "private.gfi_application_funnel" in SQL
    assert "private.gfi_application_outcomes" in SQL
    assert "private.gfi_application_source_conversion" in SQL
    assert "having count(distinct journey_id) >= 5" in SQL.lower()


def test_journey_interface_discloses_local_storage_and_cross_device_limit():
    assert "Your saved portfolio stays in this browser" in JOURNEY_JS
    assert "Clearing this browser's site data removes the local portfolio" in JOURNEY_JS
    assert "Cross-device sync is not enabled in v1" in JOURNEY_JS
    assert ".application-journey" in JOURNEY_CSS
    assert ".journey-save-button" in JOURNEY_CSS
