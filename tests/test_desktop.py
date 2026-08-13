from __future__ import annotations

from pathlib import Path

import pytest

from pdf_to_epub.converter import ConversionProgress
from pdf_to_epub.desktop import (
    DEFAULT_MODEL_LABEL,
    build_conversion_options,
    default_epub_path,
    friendly_error,
    friendly_progress,
    model_description,
    progress_stage,
)


def test_default_epub_path_uses_book_metadata(tmp_path: Path) -> None:
    pdf = tmp_path / "tarama.pdf"
    assert default_epub_path(pdf, "Çalıkuşu", "Reşat Nuri") == (
        tmp_path / "Çalıkuşu - Reşat Nuri.epub"
    )
    assert default_epub_path(pdf, "", "") == tmp_path / "tarama.epub"
    assert default_epub_path(pdf, "Tarama", "Bilinmiyor") == tmp_path / "Tarama.epub"


def test_build_conversion_options_maps_desktop_defaults(tmp_path: Path) -> None:
    pdf = tmp_path / "kitap.pdf"
    pdf.write_bytes(b"%PDF")
    output = tmp_path / "kitap.epub"

    options = build_conversion_options(
        pdf_path=pdf,
        epub_path=output,
        title=" ",
        author=" ",
        language=" ",
        model_label=DEFAULT_MODEL_LABEL,
        overwrite=True,
    )

    assert options.pdf_path == pdf.resolve()
    assert options.epub_path == output.resolve()
    assert options.metadata.title == "kitap"
    assert options.metadata.author == "Bilinmiyor"
    assert options.metadata.language == "tr"
    assert options.ocr_size == "large"
    assert options.dpi == 300
    assert options.overwrite is True
    assert options.css_path is not None


@pytest.mark.parametrize(
    ("pdf_name", "output_name", "model", "message"),
    [
        ("missing.pdf", "book.epub", DEFAULT_MODEL_LABEL, "PDF dosyası"),
        ("book.pdf", ".", DEFAULT_MODEL_LABEL, "kaydedileceği"),
        ("book.pdf", "book.txt", DEFAULT_MODEL_LABEL, ".epub"),
        ("book.pdf", "book.epub", "unknown", "OCR modeli"),
    ],
)
def test_build_conversion_options_rejects_bad_form_values(
    tmp_path: Path, pdf_name: str, output_name: str, model: str, message: str
) -> None:
    pdf = tmp_path / pdf_name
    if pdf_name == "book.pdf":
        pdf.write_bytes(b"%PDF")
    output = Path(".") if output_name == "." else tmp_path / output_name

    with pytest.raises(ValueError, match=message):
        build_conversion_options(
            pdf_path=pdf,
            epub_path=output,
            title="Book",
            author="Author",
            language="tr",
            model_label=model,
            overwrite=False,
        )


def test_desktop_messages_are_friendly_and_future_safe() -> None:
    assert "modeli" in friendly_progress("Checking and downloading OCR models")
    assert friendly_progress("Future stage") == "Future stage"
    assert "KURULUM.bat" in friendly_error(RuntimeError("Pandoc was not found on PATH"))
    assert "CUDA" in friendly_error(RuntimeError("CUDA is not available"))
    assert "base" in friendly_error(RuntimeError("CUDA out of memory"))
    assert friendly_error(RuntimeError("different failure")) == "different failure"


def test_desktop_model_guidance_and_progress_stages() -> None:
    assert "önerilen" in model_description(DEFAULT_MODEL_LABEL)
    assert model_description("not-a-model") == "OCR modelini seçin."
    assert progress_stage("Checking and downloading OCR models") == 0
    assert progress_stage("Converting PDF to Markdown with OCR") == 1
    assert progress_stage("Building EPUB with Pandoc") == 2
    assert progress_stage("Future stage") == 0


def test_desktop_formats_live_page_progress() -> None:
    reading = ConversionProgress("Reading PDF page", "ocr", 84, 327, 83)
    completed = ConversionProgress("Completed PDF page", "ocr", 84, 327, 84)

    assert friendly_progress(reading) == "327 sayfanın 84. sayfası okunuyor (%25)"
    assert friendly_progress(completed) == "84 / 327 sayfa tamamlandı (%26)"
    assert progress_stage(reading) == 1
