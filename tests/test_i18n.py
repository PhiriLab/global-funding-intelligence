"""Checks for the EN/FR interface localisation."""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
I18N = (WEB / "i18n.js").read_text(encoding="utf-8")


def _lang_block(code: str) -> str:
    # Extract the `en: { ... }` / `fr: { ... }` object body from the dictionary.
    m = re.search(code + r"\s*:\s*\{(.*?)\n\s*\}", I18N, re.S)
    assert m, f"could not find {code} dictionary block"
    return m.group(1)


def test_i18n_loads_before_app():
    assert '<script src="i18n.js"></script>' in INDEX
    assert INDEX.index('src="i18n.js"') < INDEX.index('src="app.js"')


def test_every_used_key_is_translated_in_both_languages():
    used = set(re.findall(r'data-i18n="([a-z0-9_]+)"', INDEX))
    assert used, "no data-i18n keys found in index.html"
    en, fr = _lang_block("en"), _lang_block("fr")
    missing_en = sorted(k for k in used if re.search(rf"\b{k}\s*:", en) is None)
    missing_fr = sorted(k for k in used if re.search(rf"\b{k}\s*:", fr) is None)
    assert not missing_en, f"keys used in HTML but missing from EN dict: {missing_en}"
    assert not missing_fr, f"keys used in HTML but missing from FR dict: {missing_fr}"


def test_english_fallback_text_is_retained_in_html():
    # The English copy must stay in the HTML so the site is usable without JS
    # and so existing content assertions keep passing.
    for phrase in (
        "Find funding opportunities with evidence",
        "Eligibility is never guessed",
        "Grant resources",
    ):
        assert phrase in INDEX


def test_french_is_user_selectable_and_persisted():
    assert "localStorage.setItem('gfi-lang'" in I18N
    assert "localStorage.getItem('gfi-lang')" in I18N
    assert "navigator.language" in I18N  # browser-language default
    assert "lang-switch" in I18N          # visible toggle


def test_no_machine_translation_of_funder_or_eligibility_data():
    # Guard the honesty boundary: the localisation layer must not translate
    # opportunity/funder records. It only maps a fixed chrome dictionary.
    assert "opportunities.json" not in I18N
    assert "gfiTrack" not in I18N
