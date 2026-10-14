from pathlib import Path

import pytest
import yaml

from observatory.innovation_programmes import (
    InnovationOpportunityMetadata,
    load_innovation_programmes,
    programme_index,
)

ROOT = Path(__file__).resolve().parents[1]


def test_innovation_manifest_loads_and_ids_are_unique():
    policy, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    assert policy["primary_source_only"] is True
    assert policy["unknown_stays_unknown"] is True
    assert len(programmes) >= 16
    assert len({item.id for item in programmes}) == len(programmes)


def test_first_tranche_is_present():
    _, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    by_id = programme_index(programmes)
    expected = {
        "eurostars",
        "women_techeu",
        "innosuisse_startup_innovation",
        "go_bio_next",
        "aws_preseed_seedfinancing",
        "innobooster",
        "eic_pathfinder",
        "life_programme",
        "eu_cascade_funding_fstp",
    }
    assert expected <= set(by_id)
    assert all(by_id[item].priority == "P1" for item in expected)


def test_eu_subprogrammes_dedupe_to_parent_portal():
    _, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    by_id = programme_index(programmes)
    assert by_id["eic_pathfinder"].dedupe_parent == "eu_funding_tenders"
    assert by_id["life_programme"].dedupe_parent == "eu_funding_tenders"
    assert by_id["eu_cascade_funding_fstp"].dedupe_parent == "eu_funding_tenders"


def test_ecosystem_and_meta_sources_cannot_be_mislabelled_as_grants():
    _, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    by_id = programme_index(programmes)
    assert by_id["french_tech_rise"].programme_class == "ecosystem_access"
    assert by_id["french_tech_rise"].can_publish_as_grant_without_reclassification is False
    assert by_id["eit_opportunities"].programme_class == "meta_source"
    assert by_id["eit_opportunities"].can_publish_as_grant_without_reclassification is False
    assert by_id["eu_cascade_funding_fstp"].programme_class == "cascade_funding"
    assert by_id["eu_cascade_funding_fstp"].can_publish_as_grant_without_reclassification is True


def test_eurostars_preserves_cross_border_and_global_majority_signal():
    _, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    eurostars = programme_index(programmes)["eurostars"]
    assert eurostars.cross_border_required is True
    assert eurostars.global_majority_relevance == "high"
    assert "international_collaboration" in eurostars.themes


def test_eic_pathfinder_preserves_trl_range():
    _, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    eic = programme_index(programmes)["eic_pathfinder"]
    assert (eic.trl_min, eic.trl_max) == (1, 4)


def test_every_innovation_programme_is_registered_as_a_funding_resource():
    _, programmes = load_innovation_programmes(ROOT / "config" / "innovation_programmes.yaml")
    registry = yaml.safe_load((ROOT / "config" / "funding_sources.yaml").read_text(encoding="utf-8"))
    source_ids = {item["id"] for item in registry["sources"]}
    assert {item.id for item in programmes} <= source_ids


def test_secondary_discovery_source_is_explicitly_not_primary():
    registry = yaml.safe_load((ROOT / "config" / "funding_sources.yaml").read_text(encoding="utf-8"))
    sources = {item["id"]: item for item in registry["sources"]}
    assert sources["france_i_lab"]["authority"] == "secondary"
    assert sources["france_i_lab"]["source_type"] == "discovery_only"


def test_innovation_metadata_supports_startup_spinout_and_cofunding_fields():
    meta = InnovationOpportunityMetadata(
        opportunity_class="spinout_funding",
        venture_stages=["preseed"],
        spinout_route=True,
        startup_age_limit_years=3,
        company_country_requirements=["Austria"],
        cross_border_required=False,
        women_led_target=True,
        cofunding_rate_percent=70,
        funding_instrument="non_dilutive_grant",
        programme_family="example",
        trl_min=2,
        trl_max=5,
    )
    assert meta.spinout_route is True
    assert meta.cofunding_rate_percent == 70
    assert meta.funding_instrument == "non_dilutive_grant"


def test_innovation_metadata_does_not_guess_missing_fields():
    meta = InnovationOpportunityMetadata()
    assert meta.opportunity_class is None
    assert meta.cross_border_required is None
    assert meta.women_led_target is None
    assert meta.funding_instrument == "unknown"


def test_innovation_metadata_rejects_invalid_ranges():
    with pytest.raises(ValueError):
        InnovationOpportunityMetadata(trl_min=6, trl_max=3)
    with pytest.raises(ValueError):
        InnovationOpportunityMetadata(cofunding_rate_percent=120)
