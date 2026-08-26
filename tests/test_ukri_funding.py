from observatory.sources.ukri_funding import _is_ukri_opportunity_detail


def test_ukri_rss_and_listing_urls_are_not_detail_pages():
    assert not _is_ukri_opportunity_detail('https://www.ukri.org/opportunity/')
    assert not _is_ukri_opportunity_detail('https://www.ukri.org/opportunity/feed/')
    assert not _is_ukri_opportunity_detail('https://www.ukri.org/opportunity/page/2/')


def test_ukri_real_opportunity_slug_is_detail_page():
    assert _is_ukri_opportunity_detail('https://www.ukri.org/opportunity/example-call/')
