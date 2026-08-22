from pathlib import Path

WEB = Path("web")


def test_public_web_assets_exist():
    for name in ("index.html", "styles.css", "app.js"):
        assert (WEB / name).is_file()


def test_interface_keeps_eligibility_verification_language():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "Eligibility is never guessed" in html
    assert "verify at source" in js


def test_interface_links_public_phirilab_ecosystem():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "PhiriLab/Source-to-grounded-Skill" in html
    assert "PhiriLab/gmh-research-kit" in html
    assert "PhiriLab/research-kit" in html


def test_interface_uses_primary_funder_urls():
    js = (WEB / "app.js").read_text(encoding="utf-8")
    for host in ("scienceforafrica.foundation", "idrc-crdi.ca", "tdr.who.int", "cepi.net", "ukri.org", "nihr.ac.uk", "wellcome.org", "ec.europa.eu"):
        assert host in js
