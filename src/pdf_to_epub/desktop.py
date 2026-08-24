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
from pdf_to_epub.i18n import UiLanguage, normalize_ui_language

MODEL_LABELS = {
    "Tiny — 512 px / tahmini ≈7 GB VRAM": "tiny",
    "Small — 640 px / tahmini ≈7,5 GB VRAM": "small",
    "Base — 1024 px / tahmini ≈8 GB VRAM": "base",
    "Large — 1280 px / tahmini ≈8 GB+ VRAM": "large",
    "Gundam — kırpma / tahmini ≈10 GB+ VRAM": "gundam",
}
DEFAULT_MODEL_LABEL = "Large — 1280 px / tahmini ≈8 GB+ VRAM"
ENGLISH_MODEL_LABELS = {
    "Tiny — 512 px / estimated ≈7 GB VRAM": "tiny",
    "Small — 640 px / estimated ≈7.5 GB VRAM": "small",
    "Base — 1024 px / estimated ≈8 GB VRAM": "base",
    "Large — 1280 px / estimated ≈8 GB+ VRAM": "large",
    "Gundam — cropped / estimated ≈10 GB+ VRAM": "gundam",
}
DEFAULT_ENGLISH_MODEL_LABEL = "Large — 1280 px / estimated ≈8 GB+ VRAM"
OUTPUT_FORMAT_LABELS = {
    "EPUB — modern e-kitap (önerilen)": "epub",
    "Markdown — düzenlenebilir metin (.md)": "markdown",
    "MOBI — eski Kindle cihazları (.mobi)": "mobi",
}
DEFAULT_OUTPUT_FORMAT_LABEL = "EPUB — modern e-kitap (önerilen)"
ENGLISH_OUTPUT_FORMAT_LABELS = {
    "EPUB — modern e-book (recommended)": "epub",
    "Markdown — editable text (.md)": "markdown",
    "MOBI — older Kindle devices (.mobi)": "mobi",
}
DEFAULT_ENGLISH_OUTPUT_FORMAT_LABEL = "EPUB — modern e-book (recommended)"
ThemeName = Literal["light", "dark"]

_MODEL_DESCRIPTIONS = {
    "tiny": (
        "Aynı 6,5 GB OCR motoru, 512 px. En hızlı sayfa modudur; küçük yazıları "
        "kaçırabilir. Tahmini ≈7 GB."
    ),
    "small": (
        "Aynı 6,5 GB OCR motoru, 640 px. Temiz ve büyük yazılı taramalarda hızlıdır. "
        "Tahmini ≈7,5 GB."
    ),
    "base": "Aynı 6,5 GB OCR motoru, 1024 px. Temiz taramalarda dengeli seçimdir. Tahmini ≈8 GB.",
    "large": (
        "Aynı 6,5 GB OCR motoru, 1280 px. Küçük yazılar için önerilen kalite/hız "
        "dengesidir. Tahmini ≈8 GB+."
    ),
    "gundam": (
        "Aynı 6,5 GB OCR motoru, sayfayı kırparak işler. Karmaşık düzenlerde daha doğru "
        "fakat daha yavaştır. Tahmini ≈10 GB+."
    ),
}

_ENGLISH_MODEL_DESCRIPTIONS = {
    "tiny": (
        "The same 6.5 GB OCR engine at 512 px. Fastest page mode; may miss small text. "
        "Estimated ≈7 GB."
    ),
    "small": (
        "The same 6.5 GB OCR engine at 640 px. Fast on clean scans with large text. "
        "Estimated ≈7.5 GB."
    ),
    "base": (
        "The same 6.5 GB OCR engine at 1024 px. A balanced choice for clean scans. Estimated ≈8 GB."
    ),
    "large": (
        "The same 6.5 GB OCR engine at 1280 px. Recommended quality/speed balance for "
        "small text. Estimated ≈8 GB+."
    ),
    "gundam": (
        "The same 6.5 GB OCR engine with page cropping. More accurate on complex layouts, "
        "but slower. Estimated ≈10 GB+."
    ),
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
    "Embedding full-page cover": "PDF'nin ilk sayfası tam kapak olarak ekleniyor",
}

_ENGLISH_PROGRESS_TRANSLATIONS = {
    "Checking and downloading OCR models": "Checking OCR model (may download on first use)",
    "Converting PDF to Markdown with OCR": "Reading pages with OCR",
    "Repairing line-end hyphenation": "Repairing words split across line endings",
    "Building EPUB with Pandoc": "Building EPUB file",
    "Writing Markdown output": "Writing Markdown file and images",
    "Building MOBI with Calibre": "Building MOBI file with Calibre",
    "Embedding full-page cover": "Adding the PDF's first page as the full cover",
}


def _format_remaining_time(seconds: float | None, ui_language: str = "tr") -> str:
    if seconds is None:
        return ""
    minutes = max(1, round(seconds / 60))
    hours, remaining_minutes = divmod(minutes, 60)
    if normalize_ui_language(ui_language) == "en":
        if hours and remaining_minutes:
            return f" — about {hours} hr {remaining_minutes} min remaining"
        if hours:
            return f" — about {hours} hr remaining"
        return f" — about {minutes} min remaining"
    if hours and remaining_minutes:
        return f" — tahmini {hours} sa {remaining_minutes} dk kaldı"
    if hours:
        return f" — tahmini {hours} sa kaldı"
    return f" — tahmini {minutes} dk kaldı"


def theme_preference_path() -> Path:
    """Return the per-user file used to remember the desktop theme."""
    return user_config_path("pdf-to-epub-ocr") / "theme.txt"


def language_preference_path() -> Path:
    """Return the per-user file used to remember the desktop language."""
    return user_config_path("pdf-to-epub-ocr") / "language.txt"


def load_language_preference(settings_path: Path | None = None) -> UiLanguage:
    """Load the saved UI language with a stable English fallback."""
    path = settings_path or language_preference_path()
    try:
        value = path.read_text(encoding="utf-8")
    except OSError:
        return "en"
    return normalize_ui_language(value)


def save_language_preference(language: str, settings_path: Path | None = None) -> None:
    """Persist the UI language without failing on a read-only profile."""
    path = settings_path or language_preference_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{normalize_ui_language(language)}\n", encoding="utf-8")
    except OSError:
        pass


def model_labels(ui_language: str = "tr") -> dict[str, str]:
    """Return localized model labels mapped to stable pipeline values."""
    return ENGLISH_MODEL_LABELS if normalize_ui_language(ui_language) == "en" else MODEL_LABELS


def output_format_labels(ui_language: str = "tr") -> dict[str, str]:
    """Return localized output labels mapped to stable output values."""
    return (
        ENGLISH_OUTPUT_FORMAT_LABELS
        if normalize_ui_language(ui_language) == "en"
        else OUTPUT_FORMAT_LABELS
    )


def default_model_label(ui_language: str = "tr") -> str:
    return (
        DEFAULT_ENGLISH_MODEL_LABEL
        if normalize_ui_language(ui_language) == "en"
        else DEFAULT_MODEL_LABEL
    )


def default_output_format_label(ui_language: str = "tr") -> str:
    return (
        DEFAULT_ENGLISH_OUTPUT_FORMAT_LABEL
        if normalize_ui_language(ui_language) == "en"
        else DEFAULT_OUTPUT_FORMAT_LABEL
    )


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
    all_output_labels = {**OUTPUT_FORMAT_LABELS, **ENGLISH_OUTPUT_FORMAT_LABELS}
    if output_format_label not in all_output_labels:
        raise ValueError("Geçerli bir çıktı biçimi seçin.")
    clean_author = author.strip()
    if clean_author in {"", "Bilinmiyor", "Unknown"}:
        clean_author = "Unknown"
    metadata = BookMetadata(title.strip() or pdf_path.stem, clean_author)
    return pdf_path.with_name(
        suggested_output_name(metadata, all_output_labels[output_format_label])
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
    ui_language: str = "tr",
) -> ConversionOptions:
    """Validate desktop form values and convert them to pipeline options."""
    english = normalize_ui_language(ui_language) == "en"
    output_labels = {**OUTPUT_FORMAT_LABELS, **ENGLISH_OUTPUT_FORMAT_LABELS}
    available_model_labels = {**MODEL_LABELS, **ENGLISH_MODEL_LABELS}
    if pdf_path == Path(".") or not pdf_path.is_file():
        raise ValueError(
            "Please choose a PDF file." if english else "Lütfen bir PDF dosyası seçin."
        )
    if epub_path == Path("."):
        raise ValueError(
            "Please choose where to save the output file."
            if english
            else "Lütfen çıktı dosyasının kaydedileceği yeri seçin."
        )
    if output_format_label not in output_labels:
        raise ValueError(
            "Please choose a valid output format." if english else "Geçerli bir çıktı biçimi seçin."
        )
    try:
        selected_format = output_format_from_path(epub_path)
    except ConversionError as error:
        raise ValueError(
            "The output extension must be .epub, .md, or .mobi."
            if english
            else "Çıktı uzantısı .epub, .md veya .mobi olmalıdır."
        ) from error
    if selected_format != output_labels[output_format_label]:
        raise ValueError(
            "The selected output format does not match the file extension."
            if english
            else "Seçilen çıktı biçimi ile dosya uzantısı eşleşmiyor."
        )
    if model_label not in available_model_labels:
        raise ValueError(
            "Please choose a valid OCR model." if english else "Geçerli bir OCR modeli seçin."
        )

    clean_title = title.strip() or pdf_path.stem
    clean_author = author.strip() or ("Unknown" if english else "Bilinmiyor")
    clean_language = language.strip() or "tr"
    return ConversionOptions(
        pdf_path=pdf_path.expanduser().resolve(),
        epub_path=epub_path.expanduser().resolve(),
        metadata=BookMetadata(clean_title, clean_author, language=clean_language),
        models_dir=(user_cache_path("pdf-to-epub-ocr") / "models").resolve(),
        css_path=bundled_css_path(),
        ocr_size=available_model_labels[model_label],
        dpi=300,
        overwrite=overwrite,
    )


def friendly_progress(progress: ConversionProgress | str, ui_language: str = "tr") -> str:
    """Translate known pipeline stages while preserving future messages."""
    english = normalize_ui_language(ui_language) == "en"
    if isinstance(progress, ConversionProgress):
        if progress.current_page is not None and progress.total_pages is not None:
            percentage = progress.percentage or 0
            remaining = _format_remaining_time(progress.estimated_remaining_seconds, ui_language)
            if progress.message == "Rendering PDF page":
                if english:
                    return (
                        f"Preparing page {progress.current_page} of {progress.total_pages} "
                        f"({percentage}%){remaining}"
                    )
                return (
                    f"{progress.total_pages} sayfanın {progress.current_page}. "
                    "sayfası hazırlanıyor "
                    f"(%{percentage}){remaining}"
                )
            if progress.message == "Loading OCR model and processing PDF page":
                if progress.current_page == 1:
                    if english:
                        return (
                            "Loading the OCR model onto the GPU and processing the first page "
                            f"(1 / {progress.total_pages}, {percentage}%){remaining}"
                        )
                    return (
                        "OCR modeli GPU'ya yükleniyor ve ilk sayfa işleniyor "
                        f"(1 / {progress.total_pages}, %{percentage}){remaining}"
                    )
                if english:
                    return (
                        f"Processing page {progress.current_page} of {progress.total_pages} "
                        f"with OCR ({percentage}%){remaining}"
                    )
                return (
                    f"{progress.total_pages} sayfanın {progress.current_page}. sayfası OCR ile "
                    f"işleniyor (%{percentage}){remaining}"
                )
            if english:
                return (
                    f"Completed {progress.current_page} / {progress.total_pages} pages "
                    f"({percentage}%){remaining}"
                )
            return (
                f"{progress.current_page} / {progress.total_pages} sayfa tamamlandı "
                f"(%{percentage}){remaining}"
            )
        message = progress.message
    else:
        message = progress
    translations = _ENGLISH_PROGRESS_TRANSLATIONS if english else _PROGRESS_TRANSLATIONS
    return translations.get(message, message)


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
        "Embedding full-page cover": 2,
    }
    return stages.get(message, 0)


def model_description(model_label: str, ui_language: str = "tr") -> str:
    """Return short, non-technical guidance for a desktop model choice."""
    english = normalize_ui_language(ui_language) == "en"
    available_model_labels = {**MODEL_LABELS, **ENGLISH_MODEL_LABELS}
    model = available_model_labels.get(model_label)
    if model is None:
        return "Choose a page processing mode." if english else "Sayfa işleme modunu seçin."
    descriptions = _ENGLISH_MODEL_DESCRIPTIONS if english else _MODEL_DESCRIPTIONS
    return descriptions[model]


def friendly_error(error: Exception, ui_language: str = "tr") -> str:
    """Add localized, actionable guidance to common runtime failures."""
    message = str(error)
    english = normalize_ui_language(ui_language) == "en"
    if "Pandoc was not found" in message:
        return (
            "Pandoc was not found. Open Maintenance Center and select Repair."
            if english
            else "Pandoc bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
        )
    if "Calibre ebook-convert was not found" in message:
        return (
            "Calibre was not found for MOBI output. Open Maintenance Center and select Repair."
            if english
            else "MOBI için Calibre bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
        )
    if "PyTorch is not installed" in message:
        return (
            "PyTorch was not found. Open Maintenance Center and select Repair."
            if english
            else "PyTorch bulunamadı. KURULUM.bat dosyasını yeniden çalıştırın."
        )
    if "CUDA/ROCm is not available" in message or "CUDA is not available" in message:
        if english:
            return (
                "GPU acceleration is unavailable. This OCR engine cannot run on the CPU. "
                "Check the driver for a supported NVIDIA CUDA or AMD ROCm graphics card, "
                "then open Maintenance Center and select Repair."
            )
        return (
            "GPU hızlandırması kullanılamıyor. Bu OCR motoru CPU ile çalışmaz. Desteklenen "
            "NVIDIA CUDA veya AMD ROCm ekran kartı sürücüsünü kontrol edip KURULUM.bat "
            "dosyasını yeniden çalıştırın."
        )
    if "Output already exists" in message:
        return (
            "An output file with the same name already exists. Choose another location."
            if english
            else "Aynı isimde bir çıktı dosyası zaten var. Farklı bir kayıt yeri seçin."
        )
    if "CUDA out of memory" in message or "out of memory" in message.lower():
        if english:
            return (
                "The graphics card ran out of memory. Close other GPU applications. The "
                "'base' or 'small' mode can reduce page-processing load, but the 6.5 GB "
                "base model does not change."
            )
        return (
            "Ekran kartı belleği yetmedi. Diğer GPU uygulamalarını kapatın. 'base' veya "
            "'small' sayfa işleme yükünü azaltabilir; ancak 6,5 GB ana model değişmez."
        )
    if "does not fit reliably in a 6 GB GPU" in message:
        if english:
            return (
                "This graphics card does not have enough memory for the current 6.5 GB OCR "
                "model. Tiny and small only reduce page load; they do not shrink the base "
                f"model on a 6 GB card. Details: {message}"
            )
        return (
            "Bu ekran kartının belleği mevcut 6,5 GB OCR modeline yetmiyor. Tiny ve small "
            "yalnızca sayfa yükünü azaltır; 6 GB kartta ana modeli küçültmez. Ayrıntı: "
            f"{message}"
        )
    if "not enough free VRAM" in message:
        if english:
            return (
                "There is not enough free graphics memory to load the OCR model. Close the "
                f"browser, games, and other GPU applications, then try again. Details: {message}"
            )
        return (
            "OCR modelini yüklemek için boş ekran kartı belleği kalmamış. Tarayıcı, oyun ve "
            f"GPU kullanan diğer uygulamaları kapatıp tekrar deneyin. Ayrıntı: {message}"
        )
    if "only" in message and "VRAM available" in message:
        if english:
            return (
                "Available graphics memory is low. Close the browser, games, and other GPU "
                f"applications. Details: {message}"
            )
        return (
            "Kullanılabilir ekran kartı belleği düşük. Tarayıcı, oyun ve GPU kullanan diğer "
            f"uygulamaları kapatın. Ayrıntı: {message}"
        )
    if "sm_120" in message or "cannot run kernels" in message:
        if english:
            return (
                "The installed PyTorch/CUDA version is not compatible with your graphics "
                "card. Open Maintenance Center and select Repair. Details: " + message
            )
        return (
            "Ekran kartınızla uyumlu PyTorch/CUDA sürümü kurulu değil. KURULUM.bat dosyasını "
            "yeniden çalıştırın. Ayrıntı: " + message
        )
    if "WinError 1314" in message or "privilege" in message.lower():
        if english:
            return (
                "The model cache encountered a Windows permission error. The latest release "
                "uses normal file copies; update the installation and try again. Details: "
                + message
            )
        return (
            "Model önbelleği Windows izin hatası verdi. Son sürüm normal dosya kopyalama "
            f"yöntemini kullanır; kurulumu güncelleyip tekrar deneyin. Ayrıntı: {message}"
        )
    if "Failed to extract page" in message:
        if english:
            return (
                f"OCR could not process the first page. Details: {message} Include your "
                "graphics card model and VRAM amount in the bug report."
            )
        return (
            f"OCR ilk sayfayı işleyemedi. Ayrıntı: {message} "
            "Ekran kartınızın modelini ve VRAM miktarını hata bildirimine ekleyin."
        )
    return message

