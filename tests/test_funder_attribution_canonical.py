"""One funder, one id.

The curated directory and the live feed name the same funder differently: the
directory uses a funder id ('ukri', 'eu'), the publisher uses a connector id
('ukri_funding_finder', 'eu_funding_tenders'). Telemetry recorded both, so a
funder's reach and opens were split across two rows — the month-end data showed
UKRI as 36 impressions under one id and 13 under the other, which understates the
funder by 27% in any report built from a single row.

This drives the real module in Node with both surfaces present for one funder and
asserts the emitted source_id is the funder's, and that the funder is counted once.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "support" / "funder_attribution_harness.js"
MODULE = ROOT / "web" / "opportunities.js"


@pytest.fixture(scope="module")
def emitted():
    if shutil.which("node") is None:
        pytest.skip("node is required to drive the browser module")
    out = subprocess.run(
        ["node", str(HARNESS), str(MODULE)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_connector_ids_are_recorded_under_the_funder_id(emitted):
    # The harness presents ukri_funding_finder + ukri, eu_funding_tenders, idrc.
    assert "ukri_funding_finder" not in emitted["impressions"]
    assert "eu_funding_tenders" not in emitted["impressions"]
    assert "ukri" in emitted["impressions"]
    assert "eu" in emitted["impressions"]


def test_one_funder_on_two_surfaces_counts_as_one_impression(emitted):
    # Reach means "surfaced to a visitor", so a funder shown on both the directory
    # and the feed in one page load is one impression, not two.
    assert emitted["impressions"].count("ukri") == 1
    assert len(emitted["impressions"]) == len(set(emitted["impressions"]))


def test_unaliased_ids_are_left_alone(emitted):
    # Most connector ids already match the directory; canonicalising must not touch them.
    assert "idrc" in emitted["impressions"]


def test_opens_attribute_to_the_funder_not_the_connector(emitted):
    # Opens are per click and not deduped, but both UKRI surfaces resolve to one funder.
    assert emitted["opens"].count("ukri") == 2
    assert "ukri_funding_finder" not in emitted["opens"]
