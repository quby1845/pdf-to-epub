from __future__ import annotations

from pathlib import Path

import pytest

from pdf_to_epub.converter import ConversionProgress
from pdf_to_epub.desktop import (
    DEFAULT_ENGLISH_MODEL_LABEL,
    DEFAULT_ENGLISH_OUTPUT_FORMAT_LABEL,
    DEFAULT_MODEL_LABEL,
    DEFAULT_OUTPUT_FORMAT_LABEL,
    MODEL_LABELS,
    OUTPUT_FORMAT_LABELS,
    build_conversion_options,
    default_epub_path,
    default_model_label,
    default_output_format_label,
    default_output_path,
    friendly_error,
    friendly_progress,
    load_language_preference,
    load_theme_preference,
    model_description,
    model_labels,
    output_format_labels,
    progress_stage,
    save_language_preference,
    save_theme_preference,
)


def test_default_epub_path_uses_book_metadata(tmp_path: Path) -> None:
    pdf = tmp_path / "tarama.pdf"
    assert default_epub_path(pdf, "Çalıkuşu", "Reşat Nuri") == (
        tmp_path / "Çalıkuşu - Reşat Nuri.epub"
    )
    assert default_epub_path(pdf, "", "") == tmp_path / "tarama.epub"
    assert default_epub_path(pdf, "Tarama", "Bilinmiyor") == tmp_path / "Tarama.epub"
    markdown_label = next(
        label
        for label, output_format in OUTPUT_FORMAT_LABELS.items()
        if output_format == "markdown"
    )
    assert default_output_path(pdf, "Tarama", "Bilinmiyor", markdown_label) == (
        tmp_path / "Tarama.md"
    )


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
    assert options.output_format == "epub"
    assert DEFAULT_OUTPUT_FORMAT_LABEL in OUTPUT_FORMAT_LABELS


def test_build_conversion_options_accepts_matching_markdown_format(tmp_path: Path) -> None:
    pdf = tmp_path / "kitap.pdf"
    pdf.write_bytes(b"%PDF")
    markdown_label = next(
        label
        for label, output_format in OUTPUT_FORMAT_LABELS.items()
        if output_format == "markdown"
    )
    options = build_conversion_options(
        pdf_path=pdf,
        epub_path=tmp_path / "kitap.md",
        title="Kitap",
        author="Yazar",
        language="tr",
        model_label=DEFAULT_MODEL_LABEL,
        overwrite=False,
        output_format_label=markdown_label,
    )
    assert options.output_format == "markdown"

    with pytest.raises(ValueError, match="eşleşmiyor"):
        build_conversion_options(
            pdf_path=pdf,
            epub_path=tmp_path / "kitap.epub",
            title="Kitap",
            author="Yazar",
            language="tr",
            model_label=DEFAULT_MODEL_LABEL,
            overwrite=False,
            output_format_label=markdown_label,
        )


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
    assert "KURULUM.bat" in friendly_error(
        RuntimeError("Pandoc was not found on PATH"), platform="win32"
    )
    assert "AMD ROCm" in friendly_error(
        RuntimeError("CUDA/ROCm is not available"), platform="win32"
    )
    assert "base" in friendly_error(RuntimeError("CUDA out of memory"))
    assert "6,5 GB" in friendly_error(
        RuntimeError("The current model does not fit reliably in a 6 GB GPU")
    )
    assert "uygulamaları kapatıp" in friendly_error(RuntimeError("There is not enough free VRAM"))
    assert "KURULUM.bat" in friendly_error(RuntimeError("missing sm_120 support"), platform="win32")
    assert "VRAM" in friendly_error(RuntimeError("Failed to extract page 1 layout at stage 1"))
    assert friendly_error(RuntimeError("different failure")) == "different failure"


def test_desktop_model_guidance_and_progress_stages() -> None:
    assert "önerilen" in model_description(DEFAULT_MODEL_LABEL).casefold()
    assert list(MODEL_LABELS) == [
        "Tiny — 512 px / tahmini ≈7 GB VRAM",
        "Small — 640 px / tahmini ≈7,5 GB VRAM",
        "Base — 1024 px / tahmini ≈8 GB VRAM",
        "Large — 1280 px / tahmini ≈8 GB+ VRAM",
        "Gundam — kırpma / tahmini ≈10 GB+ VRAM",
    ]
    assert set(MODEL_LABELS.values()) == {"tiny", "small", "base", "large", "gundam"}
    assert "≈8 GB+" in model_description(DEFAULT_MODEL_LABEL)
    assert "≈7 GB" in model_description(next(iter(MODEL_LABELS)))
    assert "≈7,5 GB" in model_description(list(MODEL_LABELS)[1])
    assert model_description("not-a-model") == "Sayfa işleme modunu seçin."
    assert progress_stage("Checking and downloading OCR models") == 0
    assert progress_stage("Converting PDF to Markdown with OCR") == 1
    assert progress_stage("Building EPUB with Pandoc") == 2
    assert progress_stage("Future stage") == 0


def test_desktop_formats_live_page_progress() -> None:
    reading = ConversionProgress("Rendering PDF page", "ocr", 84, 327, 83)
    loading = ConversionProgress("Loading OCR model and processing PDF page", "ocr", 1, 327, 0)
    completed = ConversionProgress("Completed PDF page", "ocr", 84, 327, 84)

    assert friendly_progress(reading) == "327 sayfanın 84. sayfası hazırlanıyor (%25)"
    assert "GPU'ya yükleniyor" in friendly_progress(loading)
    assert friendly_progress(completed) == "84 / 327 sayfa tamamlandı (%26)"
    assert progress_stage(reading) == 1

    estimated = ConversionProgress("Completed PDF page", "ocr", 40, 100, 40, 4500)
    assert "1 sa 15 dk kaldı" in friendly_progress(estimated)


def test_desktop_theme_preference_round_trip_and_safe_fallback(tmp_path: Path) -> None:
    settings = tmp_path / "settings" / "theme.txt"
    assert load_theme_preference(settings) == "light"

    save_theme_preference("dark", settings)
    assert settings.read_text(encoding="utf-8") == "dark\n"
    assert load_theme_preference(settings) == "dark"

    settings.write_text("unsupported", encoding="utf-8")
    assert load_theme_preference(settings) == "light"


def test_desktop_language_preference_round_trip_and_safe_fallback(tmp_path: Path) -> None:
    settings = tmp_path / "settings" / "language.txt"
    assert load_language_preference(settings) == "en"

    save_language_preference("en", settings)
    assert settings.read_text(encoding="utf-8") == "en\n"
    assert load_language_preference(settings) == "en"

    settings.write_text("unsupported", encoding="utf-8")
    assert load_language_preference(settings) == "en"


def test_desktop_english_labels_and_messages(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF")
    options = build_conversion_options(
        pdf_path=pdf,
        epub_path=tmp_path / "book.epub",
        title="Book",
        author="",
        language="en",
        model_label=DEFAULT_ENGLISH_MODEL_LABEL,
        overwrite=False,
        output_format_label=DEFAULT_ENGLISH_OUTPUT_FORMAT_LABEL,
        ui_language="en",
    )

    assert options.ocr_size == "large"
    assert options.metadata.author == "Unknown"
    assert default_model_label("en") == DEFAULT_ENGLISH_MODEL_LABEL
    assert default_model_label("tr") == DEFAULT_MODEL_LABEL
    assert default_output_format_label("en") == DEFAULT_ENGLISH_OUTPUT_FORMAT_LABEL
    assert model_labels("en")[DEFAULT_ENGLISH_MODEL_LABEL] == "large"
    assert output_format_labels("en")[DEFAULT_ENGLISH_OUTPUT_FORMAT_LABEL] == "epub"
    assert "recommended" in model_description(DEFAULT_ENGLISH_MODEL_LABEL, "en").casefold()
    assert "Checking OCR model" in friendly_progress("Checking and downloading OCR models", "en")
    assert "Maintenance Center" in friendly_error(
        RuntimeError("Pandoc was not found on PATH"), "en", platform="win32"
    )

    progress = ConversionProgress("Completed PDF page", "ocr", 40, 100, 40, 4500)
    assert friendly_progress(progress, "en") == (
        "Completed 40 / 100 pages (40%) — about 1 hr 15 min remaining"
    )


def test_desktop_errors_use_native_linux_and_macos_guidance() -> None:
    linux = friendly_error(RuntimeError("PyTorch is not installed"), "en", platform="linux")
    assert "./setup.sh --repair" in linux

    macos = friendly_error(RuntimeError("CUDA/ROCm is not available"), "en", platform="darwin")
    assert "Apple Silicon/Metal (MPS)" in macos
