"""Pure helpers shared by the desktop interface.

Keeping path and option handling outside Tkinter makes the user-facing workflow
testable without requiring a graphical display in CI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from platformdirs import user_cache_path, user_config_path

from pdf_to_epub.converter import (
    BookMetadata,
    ConversionError,
    ConversionOptions,
    ConversionProgress,
    bundled_css_path,
    output_format_from_path,
    suggested_output_name,
)

MODEL_LABELS = {
    "Tiny — 512 px / tahmini ≈7 GB VRAM": "tiny",
    "Small — 640 px / tahmini ≈7,5 GB VRAM": "small",
    "Base — 1024 px / tahmini ≈8 GB VRAM": "base",
    "Large — 1280 px / tahmini ≈8 GB+ VRAM": "large",
    "Gundam — kırpma / tahmini ≈10 GB+ VRAM": "gundam",
}
DEFAULT_MODEL_LABEL = "Large — 1280 px / tahmini ≈8 GB+ VRAM"
OUTPUT_FORMAT_LABELS = {
    "EPUB — modern e-kitap (önerilen)": "epub",
    "Markdown — düzenlenebilir metin (.md)": "markdown",
    "MOBI — eski Kindle cihazları (.mobi)": "mobi",
}
DEFAULT_OUTPUT_FORMAT_LABEL = "EPUB — modern e-kitap (önerilen)"
ThemeName = Literal["light", "dark"]

_MODEL_DESCRIPTIONS = {
    "tiny": "Tahmini ≈7 GB. En hızlıdır; küçük yazılarda kalite düşebilir.",
    "small": "Tahmini ≈7,5 GB. Temiz taramalarda hızlı ve yeterli olabilir.",
    "base": "Tahmini ≈8 GB. Temiz taramalar ve 8 GB kartlar için güvenli seçimdir.",
    "large": "Tahmini ≈8 GB+. Önerilen kalite/hız dengesidir; diğer GPU uygulamalarını kapatın.",
    "gundam": "Tahmini ≈10 GB+. Kırpma kullanır; tepe tüketimi sayfaya göre değişir.",
}

_PROGRESS_TRANSLATIONS = {
    "Checking and downloading OCR models": (
        "OCR modeli kontrol ediliyor (ilk seferde indirilebilir)"
    ),
    "Converting PDF to Markdown with OCR": "Sayfalar OCR ile okunuyor",
    "Repairing line-end hyphenation": "Satır sonu kelimeleri düzeltiliyor",
    "Building EPUB with Pandoc": "EPUB dosyası hazırlanıyor",
    "Writing Markdown output": "Markdown dosyası ve görseller hazırlanıyor",
    "Building MOBI with Calibre": "MOBI dosyası Calibre ile hazırlanıyor",
}


def theme_preference_path() -> Path:
    """Return the per-user file used to remember the desktop theme."""
    return user_config_path("pdf-to-epub-ocr") / "theme.txt"


def load_theme_preference(settings_path: Path | None = None) -> ThemeName:
    """Load a saved theme, falling back safely when the file is absent or invalid."""
    path = settings_path or theme_preference_path()
    try:
        value = path.read_text(encoding="utf-8").strip().casefold()
    except OSError:
        return "light"
    return "dark" if value == "dark" else "light"


def save_theme_preference(theme: ThemeName, settings_path: Path | None = None) -> None:
    """Persist a desktop theme without making the UI fail on a read-only profile."""
    path = settings_path or theme_preference_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{theme}\n", encoding="utf-8")
    except OSError:
        pass


def default_output_path(
    pdf_path: Path,
    title: str,
    author: str,
    output_format_label: str = DEFAULT_OUTPUT_FORMAT_LABEL,
) -> Path:
    """Return a friendly output path next to the selected PDF."""
    if output_format_label not in OUTPUT_FORMAT_LABELS:
        raise ValueError("Geçerli bir çıktı biçimi seçin.")
    clean_author = author.strip()
    if clean_author in {"", "Bilinmiyor", "Unknown"}:
        clean_author = "Unknown"
    metadata = BookMetadata(title.strip() or pdf_path.stem, clean_author)
    return pdf_path.with_name(
        suggested_output_name(metadata, OUTPUT_FORMAT_LABELS[output_format_label])
    )


def default_epub_path(pdf_path: Path, title: str, author: str) -> Path:
    """Backward-compatible alias for the original EPUB-only desktop helper."""
    return default_output_path(pdf_path, title, author)


def build_conversion_options(
    *,
    pdf_path: Path,
    epub_path: Path,
    title: str,
    author: str,
    language: str,
    model_label: str,
    overwrite: bool,
    output_format_label: str = DEFAULT_OUTPUT_FORMAT_LABEL,
) -> ConversionOptions:
    """Validate desktop form values and convert them to pipeline options."""
    if pdf_path == Path(".") or not pdf_path.is_file():
        raise ValueError("Lütfen bir PDF dosyası seçin.")
    if epub_path == Path("."):
        raise ValueError("Lütfen çıktı dosyasının kaydedileceği yeri seçin.")
    if output_format_label not in OUTPUT_FORMAT_LABELS:
        raise ValueError("Geçerli bir çıktı biçimi seçin.")
    try:
        selected_format = output_format_from_path(epub_path)
    except ConversionError as error:
        raise ValueError("Çıktı uzantısı .epub, .md veya .mobi olmalıdır.") from error
    if selected_format != OUTPUT_FORMAT_LABELS[output_format_label]:
        raise ValueError("Seçilen çıktı biçimi ile dosya uzantısı eşleşmiyor.")
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


def friendly_progress(progress: ConversionProgress | str) -> str:
    """Translate known pipeline stages while preserving future messages."""
    if isinstance(progress, ConversionProgress):
        if progress.current_page is not None and progress.total_pages is not None:
            percentage = progress.percentage or 0
            if progress.message == "Rendering PDF page":
                return (
                    f"{progress.total_pages} sayfanın {progress.current_page}. "
                    "sayfası hazırlanıyor "
                    f"(%{percentage})"
                )
            if progress.message == "Loading OCR model and processing PDF page":
                if progress.current_page == 1:
                    return (
                        "OCR modeli GPU'ya yükleniyor ve ilk sayfa işleniyor "
                        f"(1 / {progress.total_pages}, %{percentage})"
                    )
                return (
                    f"{progress.total_pages} sayfanın {progress.current_page}. sayfası OCR ile "
                    f"işleniyor (%{percentage})"
                )
            return (
                f"{progress.current_page} / {progress.total_pages} sayfa tamamlandı (%{percentage})"
            )
        message = progress.message
    else:
        message = progress
    return _PROGRESS_TRANSLATIONS.get(message, message)


def progress_stage(progress: ConversionProgress | str) -> int:
    """Map a pipeline message to the three-stage desktop progress indicator."""
    if isinstance(progress, ConversionProgress):
        return {"models": 0, "ocr": 1, "cleanup": 2, "epub": 2}[progress.stage]
    message = progress
    stages = {
        "Checking and downloading OCR models": 0,
        "Converting PDF to Markdown with OCR": 1,
        "Repairing line-end hyphenation": 2,
        "Building EPUB with Pandoc": 2,
        "Writing Markdown output": 2,
        "Building MOBI with Calibre": 2,
    }
    return stages.get(message, 0)


def model_description(model_label: str) -> str:
    """Return short, non-technical guidance for a desktop model choice."""
    model = MODEL_LABELS.get(model_label)
    if model is None:
        return "OCR modelini seçin."
    return _MODEL_DESCRIPTIONS[model]


def friendly_error(error: Exception) -> str:
    """Add actionable Turkish guidance to common runtime failures."""
    message = str(error)
    if "Pandoc was not found" in message:
        return "Pandoc bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
    if "Calibre ebook-convert was not found" in message:
        return "MOBI için Calibre bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
    if "PyTorch is not installed" in message:
        return "PyTorch bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
    if "CUDA is not available" in message:
        return (
            "NVIDIA CUDA kullanılamıyor. Bu OCR motoru CPU ile çalışmaz. "
            "NVIDIA sürücüsünü kontrol edip KURULUM.bat dosyasını yeniden çalıştırın."
        )
    if "Output already exists" in message:
        return "Aynı isimde bir çıktı dosyası zaten var. Farklı bir kayıt yeri seçin."
    if "CUDA out of memory" in message or "out of memory" in message.lower():
        return (
            "Ekran kartı belleği yetmedi. Diğer GPU uygulamalarını kapatın. 'base' veya "
            "'small' sayfa işleme yükünü azaltabilir; ancak 6,5 GB ana model değişmez."
        )
    if "does not fit reliably in a 6 GB GPU" in message:
        return (
            "Bu ekran kartının belleği mevcut 6,5 GB OCR modeline yetmiyor. Tiny ve small "
            "yalnızca sayfa yükünü azaltır; 6 GB kartta ana modeli küçültmez. Ayrıntı: "
            f"{message}"
        )
    if "not enough free VRAM" in message:
        return (
            "OCR modelini yüklemek için boş ekran kartı belleği kalmamış. Tarayıcı, oyun ve "
            f"GPU kullanan diğer uygulamaları kapatıp tekrar deneyin. Ayrıntı: {message}"
        )
    if "only" in message and "VRAM available" in message:
        return (
            "Kullanılabilir ekran kartı belleği düşük. Tarayıcı, oyun ve GPU kullanan diğer "
            f"uygulamaları kapatın. Ayrıntı: {message}"
        )
    if "sm_120" in message or "cannot run kernels" in message:
        return (
            "Ekran kartınızla uyumlu PyTorch/CUDA sürümü kurulu değil. KURULUM.bat dosyasını "
            "yeniden çalıştırın. Ayrıntı: " + message
        )
    if "WinError 1314" in message or "privilege" in message.lower():
        return (
            "Model önbelleği Windows izin hatası verdi. Son sürüm normal dosya kopyalama "
            f"yöntemini kullanır; kurulumu güncelleyip tekrar deneyin. Ayrıntı: {message}"
        )
    if "Failed to extract page" in message:
        return (
            f"OCR ilk sayfayı işleyemedi. Ayrıntı: {message} "
            "Ekran kartınızın modelini ve VRAM miktarını hata bildirimine ekleyin."
        )
    return message
