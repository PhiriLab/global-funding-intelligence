"""session_start must fire exactly once per session.

The original guard read a sessionStorage flag, awaited the network call, then set
the flag. Page load fires several telemetry POSTs at once, so every concurrent
caller passed the guard before any of them marked it, emitting a duplicate
session_start per session (observed live at exactly 2x, which would inflate any
session count taken from those rows). This drives the real module in Node with
racing POSTs and asserts a single send.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "support" / "session_start_harness.js"
MODULE = ROOT / "web" / "telemetry-v2.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required to drive the browser module")
def test_session_start_fires_once_despite_concurrent_telemetry_posts():
    out = subprocess.run(
        ["node", str(HARNESS), str(MODULE)],
        capture_output=True, text=True, timeout=60, check=True,
    )
    result = json.loads(out.stdout.strip().splitlines()[-1])
    assert result["session_start"] == 1, (
        f"expected exactly one session_start, got {result['session_start']}: {result['sent']}"
    )
    # The originating events must still be forwarded, with page_ready rewritten to page_view.
    assert "page_view" in result["sent"]
    assert "page_ready" not in result["sent"]
