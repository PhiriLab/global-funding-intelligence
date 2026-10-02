from pathlib import Path

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
    for field in [
        'found_relevant_opportunity', 'usefulness', 'would_return',
        'country_code', 'world_region', 'organisation_type',
        'career_stage', 'sector', 'setting_identity'
    ]:
        assert field in PULSE
    assert 'email' not in PULSE.lower()
    assert 'name="' not in PULSE.lower()

def test_database_accepts_pulse_submissions():
    assert 'gfi_usefulness_pulse' in DB
    assert 'public insert usefulness pulse' in DB
