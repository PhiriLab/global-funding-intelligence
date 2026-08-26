from observatory.sources.eu_funding_tenders import _extract_records, normalise_eu_record


def test_eu_search_results_flatten_nested_metadata():
    payload = {
        'results': [{
            'reference': 'ref-1',
            'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-TEST-01',
            'content': 'Fallback content',
            'metadata': {
                'identifier': ['HORIZON-TEST-01'],
                'title': ['Test call'],
                'status': ['31094501'],
                'deadlineDate': ['2026-12-01T17:00:00Z'],
                'frameworkProgramme': ['Horizon Europe'],
            },
        }]
    }
    records = _extract_records(payload)
    assert len(records) == 1
    assert records[0]['identifier'] == ['HORIZON-TEST-01']
    assert records[0]['url'].startswith('https://ec.europa.eu/')
    opportunity = normalise_eu_record(records[0])
    assert opportunity.external_id == 'HORIZON-TEST-01'
    assert opportunity.title == 'Test call'
    assert opportunity.primary_url == records[0]['url']
    assert opportunity.status.value == 'open'
