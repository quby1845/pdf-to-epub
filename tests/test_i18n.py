from __future__ import annotations

from pdf_to_epub.i18n import normalize_ui_language, translate


def test_translate_supports_both_languages_and_interpolation() -> None:
    assert translate("tr", "convert") == "Dönüştür"
    assert translate("en", "convert") == "Convert"
    assert translate("en", "step", number=2) == "STEP 2"


def test_unknown_language_falls_back_to_english() -> None:
    assert normalize_ui_language("unsupported") == "en"
    assert translate("unsupported", "pause") == "Pause"
