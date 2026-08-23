from observatory.sources.fogarty_funding import FogartyFundingRow, normalise_fogarty_rows, parse_fogarty_rows


HTML = '''
<table>
<tr><th>Application deadline</th><th>Funding opportunity announcement</th><th>Funding type</th></tr>
<tr><td>December 3, 2026</td><td><a href="https://grants.nih.gov/grants/guide/pa-files/PAR-25-141.html">Emerging Global Leader Award (K43) (PAR-25-141)</a></td><td>Career development</td></tr>
<tr><td>December 3, 2026</td><td><a href="https://grants.nih.gov/grants/guide/pa-files/PAR-25-142.html">Emerging Global Leader Award (K43) (PAR-25-142)</a></td><td>Career development</td></tr>
<tr><td>January 1, 2027</td><td><a href="https://example.com/RFA-XX-001">Untrusted mirror (RFA-XX-001)</a></td><td>Other</td></tr>
</table>
'''


def test_parse_fogarty_rows_accepts_only_authoritative_announcement_hosts():
    rows = parse_fogarty_rows(HTML)
    assert len(rows) == 2
    assert rows[0].deadline_text == "December 3, 2026"
    assert rows[0].announcement_url.startswith("https://grants.nih.gov/")


def test_normalise_fogarty_rows_preserves_date_without_inventing_timestamp():
    opportunities = normalise_fogarty_rows((
        FogartyFundingRow(
            deadline_text="December 3, 2026",
            title="Emerging Global Leader Award (K43) (PAR-25-141)",
            announcement_url="https://grants.nih.gov/grants/guide/pa-files/PAR-25-141.html",
            funding_type="Career development",
        ),
    ))
    item = opportunities[0]
    assert item.source_id == "fogarty"
    assert item.external_id == "PAR-25-141"
    assert item.status.value == "open"
    assert item.closing_at is None
    assert item.global_majority_access == "unclear"
    assert "December 3, 2026" in item.provenance_note
    assert "no clock time is invented" in item.provenance_note
