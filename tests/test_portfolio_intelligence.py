from pathlib import Path

WEB = Path('web')
INDEX = (WEB / 'index.html').read_text(encoding='utf-8')
PORTFOLIO = (WEB / 'portfolio-intelligence.js').read_text(encoding='utf-8')
PORTFOLIO_CSS = (WEB / 'portfolio-intelligence.css').read_text(encoding='utf-8')
READINESS = (WEB / 'application-readiness.js').read_text(encoding='utf-8')


def test_runtime_loader_orders_journey_readiness_then_portfolio():
    journey = INDEX.index('<script src="application-journey.js"></script>')
    readiness = INDEX.index('<script src="application-readiness.js"></script>')
    portfolio = INDEX.index('<script src="portfolio-intelligence.js"></script>')
    assert journey < readiness < portfolio


def test_portfolio_prioritises_deadline_readiness_and_blockers():
    for marker in ('portfolioPriority', 'computeReadiness', "readiness.state === 'blocked'", 'readiness.deadline.days', 'GFI_STAGE_ORDER'):
        assert marker in PORTFOLIO
    assert 'What needs attention next?' in PORTFOLIO
    assert '<strong>Next action:</strong>' in PORTFOLIO


def test_next_action_is_deterministic_and_does_not_infer_outcomes():
    for stage in ('saved', 'eligibility_checked', 'partner_building', 'decision_to_apply', 'drafting', 'internal_review', 'submitted', 'interview_rebuttal', 'pending'):
        assert f"journey.stage === '{stage}'" in PORTFOLIO
    assert 'do not infer an outcome from inactivity' in PORTFOLIO
    assert 'recommendedNextAction' in PORTFOLIO


def test_deadline_reminder_is_explicit_calendar_export_not_background_tracking():
    for marker in ('Add deadline reminder', 'text/calendar', 'BEGIN:VCALENDAR', 'BEGIN:VALARM', 'TRIGGER:-P14D', 'TRIGGER:-P7D', 'TRIGGER:-P2D'):
        assert marker in PORTFOLIO
    assert 'Notification.requestPermission' not in PORTFOLIO
    assert 'serviceWorker' not in PORTFOLIO
    assert 'setInterval' not in PORTFOLIO
    assert 'fetch(' not in PORTFOLIO


def test_reminder_requires_verified_or_saved_deadline():
    assert 'opportunity?.closing_at || checks.manual_deadline || journey.closing_at || null' in PORTFOLIO
    assert 'Verify a deadline to enable reminder' in PORTFOLIO
    assert 'Verify final deadline and submission requirements at the primary funder source' in PORTFOLIO


def test_portfolio_is_local_only_and_reuses_readiness_truth_model():
    assert 'No application content is uploaded.' in PORTFOLIO
    assert 'computeReadiness' in PORTFOLIO
    assert 'deadlineIntelligence' in READINESS
    assert 'localStorage' not in PORTFOLIO  # storage ownership stays in journey module
    assert 'supabase' not in PORTFOLIO.lower()


def test_portfolio_visual_assets_exist():
    assert (WEB / 'portfolio-intelligence.js').is_file()
    assert (WEB / 'portfolio-intelligence.css').is_file()
    assert '.application-portfolio' in PORTFOLIO_CSS
    assert '.portfolio-row' in PORTFOLIO_CSS
