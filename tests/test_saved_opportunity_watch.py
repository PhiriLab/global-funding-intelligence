from pathlib import Path

WEB = Path('web')
WATCH = (WEB / 'saved-opportunity-watch.js').read_text(encoding='utf-8')
PORTFOLIO = (WEB / 'portfolio-intelligence.js').read_text(encoding='utf-8')


def test_watch_tracks_material_structured_fields_and_preserves_previous_snapshot():
    for field in (
        'closing_at', 'lifecycle', 'status', 'source_state', 'global_majority_access',
        'applicant_types', 'eligible_countries', 'excluded_countries', 'lead_countries',
        'partner_countries', 'consortium_required', 'local_partner_required',
        'lead_location_rule', 'equity_or_lmic_requirement', 'eligibility', 'provenance_note'
    ):
        assert field in WATCH
    assert 'previous_snapshot: watch.last_snapshot' in WATCH
    assert 'current_snapshot: current' in WATCH
    assert 'watch.history.unshift(material)' in WATCH
    assert 'watch.history = watch.history.slice(0, 20)' in WATCH


def test_first_observation_establishes_baseline_without_false_alert():
    assert 'if (!watch.last_snapshot)' in WATCH
    assert 'watch.last_snapshot = current' in WATCH
    assert 'watch.acknowledged_at = current.captured_at' in WATCH
    baseline_block = WATCH.split('if (!watch.last_snapshot)', 1)[1].split('const differences', 1)[0]
    assert 'watch.history.unshift' not in baseline_block


def test_missing_current_record_is_not_interpreted_as_closure_or_change():
    assert 'if (!opportunity) continue;' in WATCH
    assert "String(after).toLowerCase() === 'closed'" in WATCH
    assert 'Call closure detected' in WATCH


def test_changes_remain_pending_until_explicit_acknowledgement():
    assert 'acknowledged: false' in WATCH
    assert 'Acknowledge reviewed change' in WATCH
    assert 'acknowledgeWatchChanges' in WATCH
    assert 'item.acknowledged = true' in WATCH
    assert 'Verify at primary source' in WATCH


def test_deadline_and_eligibility_changes_are_materially_classified():
    for marker in ('deadline_added', 'deadline_removed', 'deadline_changed', 'eligibility_changed', 'closed'):
        assert marker in WATCH
    assert 'Deadline change detected' in WATCH
    assert 'Eligibility evidence changed' in WATCH


def test_watch_is_local_only_and_does_not_add_server_collection():
    for forbidden in ('GFI_SUPABASE_URL', '/rest/v1/', 'gfi_application_journey_events', 'visitor_id', 'session_id', 'fingerprint'):
        assert forbidden not in WATCH


def test_portfolio_promotes_unacknowledged_source_changes_to_next_action():
    assert 'unacknowledgedWatchChanges' in PORTFOLIO
    assert 'score += 650' in PORTFOLIO
    assert 'Review and acknowledge the detected primary-source change' in PORTFOLIO
    assert 'source change' in PORTFOLIO


def test_watch_runtime_is_loaded_after_portfolio_without_changing_static_loader_order():
    assert "script.src = 'saved-opportunity-watch.js'" in PORTFOLIO
    assert "script.dataset.gfiSourceWatch = 'true'" in PORTFOLIO
    assert 'loadSavedOpportunityWatch();' in PORTFOLIO
