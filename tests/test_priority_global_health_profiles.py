import asyncio
from datetime import timezone
from pathlib import Path

import pytest

from observatory.funding_adapter import FundingSnapshot
from observatory.funding_extract import _idrc_budget_semantics, _parse_date, _parse_money, extract_structured_funding, to_opportunity
from observatory.sources.global_health_funders import (
    SOURCES,
    _OpenCallsParser,
    _same_host_detail,
    discover_idrc_opportunities,
    discover_science_for_africa_opportunities,
    extract_funder_opportunity,
    grand_challenges_canada_watch_state,
)

FIXTURES = Path(__file__).parent / "fixtures" / "funding"


def snapshot(source_id: str, html: str, candidate_links=()) -> FundingSnapshot:
    return FundingSnapshot(source_id=source_id, source_url=f"https://example.org/{source_id}", final_url=f"https://example.org/{source_id}/call", status_code=200, text=html, content_hash="fixture", candidate_links=tuple(candidate_links))


def test_science_for_africa_profile_does_not_infer_eligibility():
    html = '''<html><body><h1>Grand Challenges Africa call</h1><div>Funding Type:</div><div>Grant</div><div>Funding levels:</div><div>USD 100,000 - USD 500,000</div><div>Deadline:</div><div>30 September 2026</div><p>Principal Applicant must be based at an eligible African institution.</p></body></html>'''
    record = extract_structured_funding(snapshot("science_for_africa", html))
    opportunity = to_opportunity(record)
    assert record.min_award == 100_000 and record.max_award == 500_000
    assert opportunity.global_majority_access == "unclear"
    assert opportunity.eligible_countries == [] and opportunity.lead_countries == []


def test_idrc_ambiguous_budget_is_preserved_but_not_assigned():
    html = '''<html><body><h1>Research call</h1><div>Funded by:</div><div>IDRC</div><div>Budget:</div><div>CAD 1.5 million</div><div>Status:</div><div>Open</div></body></html>'''
    record = extract_structured_funding(snapshot("idrc", html))
    assert record.total_fund is None and record.max_award is None
    assert record.budget_text == "CAD 1.5 million"
    assert any("semantically ambiguous" in warning for warning in record.extraction_warnings)


def test_idrc_mixed_total_and_per_award_budget_asserts_nothing():
    _, minimum, maximum, total, warning = _idrc_budget_semantics("Total programme budget of CAD 5 million; grants of up to CAD 500,000 each")
    assert minimum is None and maximum is None and total is None and warning is not None
    assert _idrc_budget_semantics("Ranging from CAD50,000 to CAD300,000 per consortium member")[1:4] == (50_000, 300_000, None)
    assert _idrc_budget_semantics("Up to six grants of up to CAD1.2 million each")[1:4] == (None, 1_200_000, None)
    assert _idrc_budget_semantics("CAD 692,000")[1:4] == (None, None, None)


def test_money_parser_prefers_explicit_currency_and_spaced_thousands():
    assert _parse_money("CAD $300,000") == ("CAD", None, 300_000)
    assert _parse_money("CAD 50 000 to CAD 300 000") == ("CAD", 50_000, 300_000)


def test_named_source_timezones_are_converted_exactly_to_utc():
    summer, rolling = _parse_date("25 August 2026 3:00 pm UK time")
    assert rolling is False and summer is not None
    assert summer.tzinfo == timezone.utc
    assert summer.hour == 14
    eastern, _ = _parse_date("25 August 2026 3:00 pm ET")
    assert eastern is not None and eastern.hour == 19


def test_h1_is_preferred_over_navigation_text_for_title():
    html = '''<html><head><title>Fallback title</title></head><body><nav>Funding menu</nav><h1>Authoritative call heading</h1><div>Status:</div><div>Open</div></body></html>'''
    record = extract_structured_funding(snapshot("idrc", html))
    assert record.title == "Authoritative call heading"


def test_only_live_verified_detail_sources_are_structured():
    assert SOURCES["science_for_africa"].structured is True
    assert SOURCES["idrc"].structured is True
    for source_id in ("tdr_who", "elrha", "cepi", "grand_challenges_canada", "novo_nordisk_foundation"):
        assert SOURCES[source_id].structured is False


def test_non_structured_sources_cannot_reach_structured_extraction():
    for source_id in ("tdr_who", "elrha", "cepi", "grand_challenges_canada", "novo_nordisk_foundation"):
        with pytest.raises(ValueError):
            asyncio.run(extract_funder_opportunity(source_id, "https://example.org/call"))


def test_real_fixtures_do_not_invent_eligibility_when_present():
    for filename, source_id in (("idrc_stisa_2034.html", "idrc"), ("sfa_gen_impact_eoi.html", "science_for_africa")):
        path = FIXTURES / filename
        if not path.exists():
            continue
        record = extract_structured_funding(snapshot(source_id, path.read_text()))
        opportunity = to_opportunity(record)
        assert opportunity.global_majority_access == "unclear"
        assert opportunity.lead_countries == []


def test_idrc_open_calls_parser_stops_before_closed_archive():
    html = '''<h2>Open calls</h2><a href="/en/funding/stisa-2034">STISA</a><a href="/en/funding/anesa">ANeSA</a><h2>Closed calls</h2><a href="/en/funding/old-call">Old call</a>'''
    parser = _OpenCallsParser()
    parser.feed(html)
    assert parser.links == ["/en/funding/stisa-2034", "/en/funding/anesa"]


def test_detail_url_filters_reject_cross_host_and_index_pages():
    assert _same_host_detail("idrc", "https://idrc-crdi.ca/en/funding/stisa-2034") == "https://idrc-crdi.ca/en/funding/stisa-2034"
    assert _same_host_detail("idrc", "https://evil.example/en/funding/stisa-2034") is None
    assert _same_host_detail("idrc", "https://idrc-crdi.ca/en/funding/applying") is None
    assert _same_host_detail("science_for_africa", "https://scienceforafrica.foundation/funding") is None
    assert _same_host_detail("science_for_africa", "https://scienceforafrica.foundation/funding-resources/tool") is None


def test_science_for_africa_empty_index_is_valid_empty_discovery(monkeypatch):
    async def fake_index(source_id):
        assert source_id == "science_for_africa"
        return snapshot(source_id, "<html><body>No available opportunities</body></html>")

    monkeypatch.setattr("observatory.sources.global_health_funders.fetch_funder_index", fake_index)
    assert asyncio.run(discover_science_for_africa_opportunities(limit=20)) == ()


def test_idrc_discovery_uses_only_open_calls_section(monkeypatch):
    html = '''<h2>Open calls</h2><a href="/en/funding/stisa-2034">STISA</a><a href="/en/funding/anesa">ANeSA</a><h2>Closed calls</h2><a href="/en/funding/old-call">Old</a>'''

    async def fake_index(source_id):
        assert source_id == "idrc"
        return snapshot(source_id, html)

    monkeypatch.setattr("observatory.sources.global_health_funders.fetch_funder_index", fake_index)
    urls = asyncio.run(discover_idrc_opportunities(limit=10))
    assert urls == (
        "https://idrc-crdi.ca/en/funding/stisa-2034",
        "https://idrc-crdi.ca/en/funding/anesa",
    )


def test_gcc_watcher_accepts_only_explicit_empty_state(monkeypatch):
    async def fake_index(source_id):
        assert source_id == "grand_challenges_canada"
        return snapshot(source_id, "<p>There are currently no open funding opportunities.</p>")

    monkeypatch.setattr("observatory.sources.global_health_funders.fetch_funder_index", fake_index)
    empty, note = asyncio.run(grand_challenges_canada_watch_state())
    assert empty is True
    assert "no open funding opportunities" in note.lower()


def test_gcc_watcher_escalates_changed_or_ambiguous_state(monkeypatch):
    async def fake_index(source_id):
        assert source_id == "grand_challenges_canada"
        return snapshot(source_id, "<h2>Apply for funding</h2><p>See current challenge opportunities.</p>")

    monkeypatch.setattr("observatory.sources.global_health_funders.fetch_funder_index", fake_index)
    empty, note = asyncio.run(grand_challenges_canada_watch_state())
    assert empty is False
    assert "verify" in note.lower()
