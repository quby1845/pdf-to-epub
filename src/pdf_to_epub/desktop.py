"""Pure helpers shared by the desktop interface.

Keeping path and option handling outside Tkinter makes the user-facing workflow
testable without requiring a graphical display in CI.
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_cache_path

from pdf_to_epub.converter import (
    BookMetadata,
    ConversionOptions,
    bundled_css_path,
    suggested_output_name,
)

MODEL_LABELS = {
    "tiny — en hızlı / en düşük kalite": "tiny",
    "small — düşük VRAM": "small",
    "base — uyumlu": "base",
    "large — dengeli (önerilen)": "large",
    "gundam — en iyi kalite / 8+ GB VRAM": "gundam",
}
DEFAULT_MODEL_LABEL = "large — dengeli (önerilen)"

_PROGRESS_TRANSLATIONS = {
    "Checking and downloading OCR models": (
        "OCR modeli kontrol ediliyor (ilk seferde indirilebilir)"
    ),
    "Converting PDF to Markdown with OCR": "Sayfalar OCR ile okunuyor",
    "Repairing line-end hyphenation": "Satır sonu kelimeleri düzeltiliyor",
    "Building EPUB with Pandoc": "EPUB dosyası hazırlanıyor",
}


def default_epub_path(pdf_path: Path, title: str, author: str) -> Path:
    """Return a friendly output path next to the selected PDF."""
    clean_author = author.strip()
    if clean_author in {"", "Bilinmiyor", "Unknown"}:
        clean_author = "Unknown"
    metadata = BookMetadata(title.strip() or pdf_path.stem, clean_author)
    return pdf_path.with_name(suggested_output_name(metadata))


def build_conversion_options(
    *,
    pdf_path: Path,
    epub_path: Path,
    title: str,
    author: str,
    language: str,
    model_label: str,
    overwrite: bool,
) -> ConversionOptions:
    """Validate desktop form values and convert them to pipeline options."""
    if pdf_path == Path(".") or not pdf_path.is_file():
        raise ValueError("Lütfen bir PDF dosyası seçin.")
    if epub_path == Path("."):
        raise ValueError("Lütfen EPUB dosyasının kaydedileceği yeri seçin.")
    if epub_path.suffix.lower() != ".epub":
        raise ValueError("Çıktı dosyasının uzantısı .epub olmalıdır.")
    if model_label not in MODEL_LABELS:
        raise ValueError("Geçerli bir OCR modeli seçin.")

    clean_title = title.strip() or pdf_path.stem
    clean_author = author.strip() or "Bilinmiyor"
    clean_language = language.strip() or "tr"
    return ConversionOptions(
        pdf_path=pdf_path.expanduser().resolve(),
        epub_path=epub_path.expanduser().resolve(),
        metadata=BookMetadata(clean_title, clean_author, language=clean_language),
        models_dir=(user_cache_path("pdf-to-epub-ocr") / "models").resolve(),
        css_path=bundled_css_path(),
        ocr_size=MODEL_LABELS[model_label],
        dpi=300,
        overwrite=overwrite,
    )


def friendly_progress(message: str) -> str:
    """Translate known pipeline stages while preserving future messages."""
    return _PROGRESS_TRANSLATIONS.get(message, message)


def friendly_error(error: Exception) -> str:
    """Add actionable Turkish guidance to common runtime failures."""
    message = str(error)
    if "Pandoc was not found" in message:
        return "Pandoc bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
    if "PyTorch is not installed" in message:
        return "PyTorch bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
    if "CUDA is not available" in message:
        return "NVIDIA CUDA kullanılamıyor; dönüşüm çok yavaş olabilir veya çalışmayabilir."
    if "Output already exists" in message:
        return "Aynı isimde bir EPUB zaten var. Farklı bir kayıt yeri seçin."
    if "CUDA out of memory" in message or "out of memory" in message.lower():
        return "Ekran kartı belleği yetmedi. OCR modelini 'base' veya 'small' seçip tekrar deneyin."
    return message
