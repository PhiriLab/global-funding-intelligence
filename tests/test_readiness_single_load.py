"""Regression: application-readiness.js must be evaluated exactly once.

It was loaded both by index.html's static <script> tag and by a dynamic injector
in application-journey.js, so its top-level `const readinessStyle` was redeclared
in the shared global scope, throwing a SyntaxError on every page load.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def test_index_loads_readiness_exactly_once():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert index.count('src="application-readiness.js"') == 1


def test_application_journey_does_not_inject_readiness():
    journey = (WEB / "application-journey.js").read_text(encoding="utf-8")
    # Guard the injection *code*, not the filename (a comment may mention it).
    assert "readinessScript" not in journey
    assert ".src = 'application-readiness.js'" not in journey
