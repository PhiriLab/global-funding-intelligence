import asyncio
from datetime import datetime, timezone

import pytest

from observatory.funding_adapter import FundingSnapshot
from observatory.sources import european_innovation_spinout as eis

NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def snapshot(source_id: str, url: str, html: str, content_hash: str = "spin123"):
    return FundingSnapshot(
        source_id=source_id,
        source_url=url,
        final_url=url,
        status_code=200,
        text=html,
        content_hash=content_hash,
        candidate_links=(),
    )


def test_go_bio_next_preserves_phase_specific_applicant_routes(monkeypatch):
    html = """
    <html><body><h1>GO-Bio next</h1>
    <p>Startdatum 16. März 2026 Enddatum 15. September 2026</p>
    <p>Antragsberechtigt für die erste Förderphase sind Hochschulen und Forschungseinrichtungen, an denen die Gründungsteams angesiedelt sind.</p>
    <p>Antragsberechtigt für die zweite Förderphase sind kleine technologieorientierte Kapitalgesellschaften, die die Voraussetzungen der KMU Definition der EU erfüllen.</p>
    <p>Ein Quereinstieg in die zweite Förderphase ist möglich, wenn die Gründung des Unternehmens vor nicht länger als drei Jahren aus einer Hochschule oder Forschungseinrichtung heraus erfolgte.</p>
    <p>Das Antragsverfahren ist zweistufig angelegt.</p>
    <p>Stichtagen 15. März und 15. September.</p>
    </body></html>
    """

    async def fake_fetch(*args, **kwargs):
        return snapshot("go_bio_next", eis.GO_BIO_NEXT, html)

    monkeypatch.setattr(eis, "fetch_primary_html", fake_fetch)
    phase1, phase2 = asyncio.run(eis.fetch_go_bio_next_opportunities(now=NOW))
    assert phase1.external_id == "go-bio-next-phase-1-2026-09"
    assert phase2.external_id == "go-bio-next-phase-2-2026-09"
    assert phase1.status.value == "open"
    assert phase1.global_majority_access == "restricted"
    assert phase2.global_majority_access == "unclear"
    assert phase1.consortium_required is False
    assert phase2.consortium_required is False
    assert "university" in phase1.applicant_types
    assert "small technology-oriented company" in phase2.applicant_types
    assert phase1.closing_at == datetime(2026, 9, 15, 21, 59, tzinfo=timezone.utc)
    assert "three years" in (phase2.provenance_note or "")


def test_go_bio_contract_change_fails_closed(monkeypatch):
    async def fake_fetch(*args, **kwargs):
        return snapshot("go_bio_next", eis.GO_BIO_NEXT, "<h1>GO-Bio next</h1><p>Changed rules</p>")

    monkeypatch.setattr(eis, "fetch_primary_html", fake_fetch)
    with pytest.raises(ValueError, match="no longer matches"):
        asyncio.run(eis.fetch_go_bio_next_opportunities(now=NOW))


def test_aws_deep_tech_splits_preseed_and_seedfinancing(monkeypatch):
    preseed_html = """
    <html><body><h1>aws Preseed - Deep Tech</h1>
    <p>Funding volume up to €267,000</p>
    <p>Submission deadline ongoing</p>
    <p>Company size natural persons Microenterprises</p>
    <p>Development phase Pre-foundation phase up to 6 months after entry of a company in the commercial register</p>
    </body></html>
    """
    seed_html = """
    <html><body><h1>aws Seedfinancing - Deep Tech</h1>
    <p>Funding volume up to €889,000</p>
    <p>Submission deadline ongoing</p>
    <p>Company size Small enterprises</p>
    <p>Foundation phase: up to 5 years after start-up; application up to 54 months after start-up</p>
    <p>conditionally refundable grant</p>
    </body></html>
    """

    async def fake_fetch(source_id, url, **kwargs):
        if url == eis.AWS_PRESEED_DEEP_TECH:
            return snapshot(source_id, url, preseed_html, "pre")
        return snapshot(source_id, url, seed_html, "seed")

    monkeypatch.setattr(eis, "fetch_primary_html", fake_fetch)
    preseed, seed = asyncio.run(eis.fetch_aws_deep_tech_opportunities(now=NOW))
    assert preseed.status.value == "rolling"
    assert seed.status.value == "rolling"
    assert preseed.currency == "EUR"
    assert seed.currency == "EUR"
    assert preseed.max_award == 300_000
    assert seed.max_award == 1_000_000
    assert "standard maximum of EUR 267,000" in (preseed.provenance_note or "")
    assert "conditionally refundable grant" in (seed.provenance_note or "")
    assert preseed.global_majority_access == "unclear"
    assert seed.global_majority_access == "unclear"


def test_aws_contract_change_fails_closed(monkeypatch):
    async def fake_fetch(source_id, url, **kwargs):
        return snapshot(source_id, url, "<h1>Changed aws programme</h1>")

    monkeypatch.setattr(eis, "fetch_primary_html", fake_fetch)
    with pytest.raises(ValueError, match="no longer matches"):
        asyncio.run(eis.fetch_aws_deep_tech_opportunities(now=NOW))
