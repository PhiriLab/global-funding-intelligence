from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from observatory.funding_adapter import fetch_primary_html
from observatory.funding_extract import visible_lines
from observatory.funding_models import Opportunity, OpportunityStatus

GO_BIO_NEXT = "https://www.ptj.de/foerdermoeglichkeiten/lebenswissenschaften/go-bio-next"
AWS_PRESEED_DEEP_TECH = "https://www.aws.at/en/aws-preseed-deep-tech/"
AWS_SEEDFINANCING_DEEP_TECH = "https://www.aws.at/en/aws-seedfinancing-deep-tech/"


def _text(html: str) -> str:
    return " ".join(" ".join(visible_lines(html)).split())


def _require_contract(text: str, markers: tuple[str, ...], label: str) -> None:
    lowered = text.casefold()
    missing = [marker for marker in markers if marker.casefold() not in lowered]
    if missing:
        raise ValueError(f"{label} page no longer matches the reviewed structured contract: missing {missing}")


def _go_bio_deadline() -> datetime:
    return datetime(2026, 9, 15, 23, 59, tzinfo=ZoneInfo("Europe/Berlin")).astimezone(timezone.utc)


async def fetch_go_bio_next_opportunities(*, now: datetime | None = None) -> tuple[Opportunity, ...]:
    now = now or datetime.now(timezone.utc)
    snapshot = await fetch_primary_html(
        "go_bio_next",
        GO_BIO_NEXT,
        keywords=("go-bio", "förderphase", "hochschulen", "forschungseinrichtungen", "kapitalgesellschaften"),
    )
    text = _text(snapshot.text)
    _require_contract(
        text,
        (
            "Startdatum 16. März 2026",
            "Enddatum 15. September 2026",
            "Antragsberechtigt für die erste Förderphase sind Hochschulen und Forschungseinrichtungen",
            "Antragsberechtigt für die zweite Förderphase sind kleine technologieorientierte Kapitalgesellschaften",
            "Das Antragsverfahren ist zweistufig angelegt",
            "15. März und 15. September",
        ),
        "GO-Bio next",
    )
    closing_at = _go_bio_deadline()
    status = OpportunityStatus.closed if now > closing_at else OpportunityStatus.open
    if status == OpportunityStatus.closed:
        return ()

    common_note = (
        "GO-Bio next is a two-stage BMFTR/PtJ life-science transfer programme. Project sketches may be submitted at the 15 March and 15 September cut-offs; the current PtJ page lists 15 September 2026 as the active end date, and the official phase submission guidance sets the cut-off at 23:59. "
        "Each funding phase can run for up to three years. Award amount and funding rate are not flattened into this record because they depend on phase, applicant and eligible work packages."
    )
    phase1 = Opportunity(
        source_id="go_bio_next",
        external_id="go-bio-next-phase-1-2026-09",
        title="GO-Bio next — Phase 1 research-to-spin-out",
        funder="German Federal Ministry of Research, Technology and Space (BMFTR)",
        programme="GO-Bio next — Phase 1",
        primary_url=snapshot.final_url,
        status=status,
        applicant_types=["university", "research institution", "academic founding team"],
        consortium_required=False,
        lead_location_rule="Phase 1 is for universities and research institutions hosting founding teams developing an independent life-science research group in Germany toward commercialisation and spin-out.",
        closing_at=closing_at,
        global_majority_access="restricted",
        source_checked_at=now,
        provenance_note=(
            common_note
            + " Phase 1 exclusively funds individual projects of universities/research institutions and develops proof-of-concept plus a commercialisation/spin-out strategy."
        ),
        raw_source_hash=snapshot.content_hash,
    )
    phase2 = Opportunity(
        source_id="go_bio_next",
        external_id="go-bio-next-phase-2-2026-09",
        title="GO-Bio next — Phase 2 spin-out company development",
        funder="German Federal Ministry of Research, Technology and Space (BMFTR)",
        programme="GO-Bio next — Phase 2",
        primary_url=snapshot.final_url,
        status=status,
        applicant_types=["small technology-oriented company", "EU SME spin-out"],
        consortium_required=False,
        lead_location_rule="Phase 2 is for small technology-oriented limited companies meeting the EU SME definition; normally the company results from Phase 1. Cross-entry is permitted only under the current source-defined spin-out, rights and own-contribution conditions.",
        closing_at=closing_at,
        global_majority_access="unclear",
        source_checked_at=now,
        provenance_note=(
            common_note
            + " Phase 2 exclusively funds individual projects of the founding company. The PtJ page permits cross-entry where the company was spun out from a university/research institution no more than three years earlier, holds commercialisation rights and can provide the required own contribution. Direct country eligibility for a cross-entry company is not inferred beyond the source text."
        ),
        raw_source_hash=snapshot.content_hash,
    )
    return phase1, phase2


async def fetch_aws_deep_tech_opportunities(*, now: datetime | None = None) -> tuple[Opportunity, ...]:
    now = now or datetime.now(timezone.utc)
    preseed_snapshot = await fetch_primary_html(
        "aws_preseed_seedfinancing",
        AWS_PRESEED_DEEP_TECH,
        keywords=("preseed", "deep tech", "funding", "ongoing", "microenterprises"),
    )
    seed_snapshot = await fetch_primary_html(
        "aws_preseed_seedfinancing",
        AWS_SEEDFINANCING_DEEP_TECH,
        keywords=("seedfinancing", "deep tech", "funding", "ongoing", "small enterprises"),
    )
    preseed_text = _text(preseed_snapshot.text)
    seed_text = _text(seed_snapshot.text)

    _require_contract(
        preseed_text,
        (
            "Funding volume up to €267,000",
            "Submission deadline ongoing",
            "natural persons",
            "Microenterprises",
            "Pre-foundation phase",
            "up to 6 months after entry of a company in the commercial register",
        ),
        "aws Preseed Deep Tech",
    )
    _require_contract(
        seed_text,
        (
            "Funding volume up to €889,000",
            "Submission deadline ongoing",
            "Small enterprises",
            "application up to 54 months after start-up",
            "conditionally refundable grant",
        ),
        "aws Seedfinancing Deep Tech",
    )

    preseed = Opportunity(
        source_id="aws_preseed_seedfinancing",
        external_id="aws-preseed-deep-tech",
        title="aws Preseed — Deep Tech",
        funder="Austria Wirtschaftsservice (aws)",
        programme="aws Preseed — Deep Tech",
        primary_url=preseed_snapshot.final_url,
        status=OpportunityStatus.rolling,
        applicant_types=["natural person", "microenterprise", "deep-tech founding team"],
        consortium_required=False,
        lead_location_rule="The reviewed public page defines pre-foundation and up-to-six-month post-registration stages; organisation/location eligibility must still be verified in the binding programme document and funding contract.",
        currency="EUR",
        max_award=300_000,
        rolling=True,
        global_majority_access="unclear",
        source_checked_at=now,
        provenance_note=(
            "aws Preseed Deep Tech is an ongoing grant route for deep-tech founding projects. The public page gives a standard maximum of EUR 267,000; the maximum can rise to EUR 300,000 when the gender bonus applies. The highest funding intensity is 80%, or up to 90% with the gender bonus. The binding programme document, contract and aws guideline remain authoritative. GFI therefore does not infer applicant-country eligibility from the operator's jurisdiction."
        ),
        raw_source_hash=preseed_snapshot.content_hash,
    )
    seed = Opportunity(
        source_id="aws_preseed_seedfinancing",
        external_id="aws-seedfinancing-deep-tech",
        title="aws Seedfinancing — Deep Tech",
        funder="Austria Wirtschaftsservice (aws)",
        programme="aws Seedfinancing — Deep Tech",
        primary_url=seed_snapshot.final_url,
        status=OpportunityStatus.rolling,
        applicant_types=["small enterprise", "deep-tech startup", "deep-tech scale-up"],
        consortium_required=False,
        lead_location_rule="The reviewed public page covers small independent enterprises and applications up to 54 months after start-up; organisation/location eligibility must still be verified in the binding programme document and funding contract.",
        currency="EUR",
        max_award=1_000_000,
        rolling=True,
        global_majority_access="unclear",
        source_checked_at=now,
        provenance_note=(
            "aws Seedfinancing Deep Tech is an ongoing, conditionally refundable grant for applied-R&D-based start-up/scale-up projects. The public page gives a standard maximum of EUR 889,000; the maximum can rise to EUR 1,000,000 when the gender bonus applies. Public funding intensity is 80%, or up to 90% with the gender bonus, with own-funds requirements. The binding programme document, contract and aws guideline remain authoritative. GFI does not infer applicant-country eligibility from the operator's jurisdiction."
        ),
        raw_source_hash=seed_snapshot.content_hash,
    )
    return preseed, seed
