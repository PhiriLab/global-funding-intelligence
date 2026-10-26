from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text()
PULSE = (ROOT / "web" / "impact-pulse.js").read_text()
DB = (ROOT / "db" / "supabase_evaluation.sql").read_text()

def test_impact_pulse_is_loaded_after_opportunities():
    assert 'src="opportunities.js"' in INDEX
    assert 'src="impact-pulse.js"' in INDEX
    assert INDEX.index('src="impact-pulse.js"') > INDEX.index('src="opportunities.js"')

def test_impact_pulse_posts_only_non_identifying_outcomes():
    assert 'gfi_usefulness_pulse' in PULSE
    payload_match = re.search(r"const payload = \\{(.*?)\\n\\s*\\};", PULSE, re.DOTALL)
    assert payload_match, "Impact-pulse payload definition not found"
    payload = payload_match.group(1)

    approved_fields = [
        'found_relevant_opportunity', 'usefulness', 'would_return',
        'country_code', 'world_region', 'organisation_type',
        'career_stage', 'sector', 'setting_identity', 'comment'
    ]
    for field in approved_fields:
        assert re.search(rf"\\b{re.escape(field)}\\s*:", payload)

    forbidden_fields = ['email', 'name', 'full_name', 'proposal_text', 'contact_details']
    for field in forbidden_fields:
        assert not re.search(rf"\\b{re.escape(field)}\\s*:", payload, re.IGNORECASE)

def test_database_accepts_pulse_submissions():
    assert 'gfi_usefulness_pulse' in DB
    assert 'public insert usefulness pulse' in DB
