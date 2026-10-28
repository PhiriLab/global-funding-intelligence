from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text()
OPPORTUNITIES = (ROOT / "web" / "opportunities.js").read_text()
PULSE = (ROOT / "web" / "impact-pulse.js").read_text()
DB = (ROOT / "db" / "supabase_evaluation.sql").read_text()


def test_impact_pulse_is_loaded_after_opportunities():
    assert 'src="opportunities.js"' in INDEX
    assert 'src="impact-pulse.js"' in INDEX
    assert INDEX.index('src="impact-pulse.js"') > INDEX.index('src="opportunities.js"')


def test_only_one_usefulness_form_and_submission_path():
    # The canonical form predates this PR. The enhancement must not create a
    # second instrument, submission path, or incompatible sponsor denominator.
    assert OPPORTUNITIES.count('id="usefulnessPulseForm"') == 1
    assert 'installUsefulnessPulse();' in OPPORTUNITIES
    assert "document.getElementById('usefulnessPulseForm')" in PULSE
    assert "document.getElementById('usefulnessPulse')" in PULSE
    assert "a.source-link" in PULSE
    assert 'href="#usefulnessPulse"' in PULSE
    assert "<form" not in PULSE
    assert "fetch(" not in PULSE


def test_existing_pulse_posts_only_approved_non_identifying_fields():
    assert 'gfi_usefulness_pulse' in OPPORTUNITIES
    submit = OPPORTUNITIES.split("async function submitUsefulnessPulse(event)", 1)[1]
    payload_match = re.search(r"const body = \{(.*?)\n\s*\};", submit, re.DOTALL)
    assert payload_match, "Canonical usefulness-pulse payload not found"
    payload = payload_match.group(1)

    approved_fields = [
        'found_relevant_opportunity', 'usefulness', 'would_return',
        'country_code', 'world_region', 'organisation_type',
        'career_stage', 'sector', 'setting_identity', 'comment'
    ]
    for field in approved_fields:
        assert re.search(rf"\b{re.escape(field)}\s*:", payload)

    forbidden_fields = ['email', 'name', 'full_name', 'proposal_text', 'contact_details']
    for field in forbidden_fields:
        assert not re.search(rf"\b{re.escape(field)}\s*:", payload, re.IGNORECASE)


def test_database_accepts_pulse_submissions():
    assert 'gfi_usefulness_pulse' in DB
    assert 'public insert usefulness pulse' in DB
