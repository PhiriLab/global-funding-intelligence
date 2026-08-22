from pathlib import Path
import re

WEB = Path("web")
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "app.js").read_text(encoding="utf-8")
CSS = (WEB / "styles.css").read_text(encoding="utf-8")


def test_public_web_assets_exist():
    for name in ("index.html", "styles.css", "app.js"):
        assert (WEB / name).is_file()


def test_interface_keeps_eligibility_verification_language():
    assert "Eligibility is never guessed" in INDEX
    assert "verify at source" in APP


def test_interface_links_public_phirilab_ecosystem():
    assert "PhiriLab/Source-to-grounded-Skill" in INDEX
    assert "PhiriLab/gmh-research-kit" in INDEX
    assert "PhiriLab/research-kit" in INDEX


def test_interface_uses_primary_funder_urls():
    for host in ("scienceforafrica.foundation", "idrc-crdi.ca", "tdr.who.int", "cepi.net", "ukri.org", "nihr.ac.uk", "wellcome.org", "ec.europa.eu"):
        assert host in APP


def test_internal_navigation_targets_exist():
    targets = set(re.findall(r'id="([^"]+)"', INDEX))
    hrefs = re.findall(r'href="#([^"]+)"', INDEX)
    missing = sorted(set(hrefs) - targets)
    assert not missing, f"Missing internal anchor targets: {missing}"


def test_theme_toggle_is_fully_wired():
    assert 'id="themeToggle"' in INDEX
    assert "localStorage.setItem('gfi-theme'" in APP
    assert 'html[data-theme="dark"]' in CSS
    assert "prefers-color-scheme: dark" in APP


def test_resource_detail_controls_are_present_and_wired():
    assert 'id="resourceDialog"' in INDEX
    assert 'data-details=' in APP
    assert 'showModal()' in APP
    assert 'Open primary source' in APP


def test_quick_resource_filters_are_wired():
    assert 'data-filter-region="UK"' in INDEX
    assert 'data-filter-region="Europe"' in INDEX
    assert 'data-filter-region="global_majority"' in INDEX
    assert 'data-search="global health"' in INDEX
    assert "querySelectorAll('[data-filter-region]')" in APP
    assert "querySelectorAll('[data-search]')" in APP


def test_all_static_external_buttons_have_real_https_targets():
    urls = re.findall(r'href="(https://[^"]+)"', INDEX)
    assert urls
    assert all(url.startswith("https://") for url in urls)
    assert all("example.com" not in url for url in urls)


def test_about_and_grant_resource_sections_exist():
    assert 'id="about"' in INDEX
    assert 'id="resources"' in INDEX
    assert "Prof. Peter Phiri, PhD" in INDEX
    assert "What is covered — and how to use it" in INDEX
