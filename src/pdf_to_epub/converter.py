"""Testable conversion pipeline built around pdf-craft and Pandoc."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from pdf_to_epub.model_cache import configure_huggingface_cache

logger = logging.getLogger(__name__)

_MINIMUM_TOTAL_VRAM_GIB = 7.0
_MINIMUM_START_VRAM_GIB = 5.5
_MINIMUM_FREE_VRAM_GIB = 6.5

_LETTER = r"[^\W\d_]"
_VISIBLE_HYPHENS = r"\-\u2010\u2011"
_TURKISH_INLINE_SUFFIX_STARTS = (
    "acak",
    "acağı",
    "ecek",
    "eceği",
    "dık",
    "dik",
    "duk",
    "dük",
    "tık",
    "tik",
    "tuk",
    "tük",
    "mış",
    "miş",
    "muş",
    "müş",
    "ıyor",
    "iyor",
    "uyor",
    "üyor",
    "makt",
    "mekt",
    "lığ",
    "liğ",
    "luğ",
    "lüğ",
    "lar",
    "ler",
    "sız",
    "siz",
    "suz",
    "süz",
)
_TURKISH_EXACT_SUFFIX_FRAGMENTS = frozenset(
    {
        "lar",
        "ler",
        "lık",
        "lik",
        "luk",
        "lük",
        "dan",
        "den",
        "tan",
        "ten",
        "dır",
        "dir",
        "dur",
        "dür",
        "tır",
        "tir",
        "tur",
        "tür",
        "mak",
        "mek",
        "ken",
        "ınca",
        "ince",
        "unca",
        "ünce",
        "ıp",
        "ip",
        "up",
        "üp",
    }
)


class ConversionError(RuntimeError):
    """Raised when input validation or an external conversion step fails."""


@dataclass(frozen=True)
class BookMetadata:
    title: str
    author: str = "Unknown"
    publisher: str = ""
    language: str = "en"


@dataclass(frozen=True)
class ConversionOptions:
    pdf_path: Path
    epub_path: Path
    metadata: BookMetadata
    models_dir: Path
    work_parent: Path | None = None
    css_path: Path | None = None
    ocr_size: str = "gundam"
    dpi: int = 300
    keep_intermediates: bool = False
    overwrite: bool = False


@dataclass(frozen=True)
class ConversionResult:
    epub_path: Path
    work_dir: Path
    elapsed_seconds: float
    hyphenation_fixes: int
    intermediates_kept: bool


ProgressStage = Literal["models", "ocr", "cleanup", "epub"]


@dataclass(frozen=True)
class ConversionProgress:
    """Structured conversion status suitable for a CLI or desktop progress bar."""

    message: str
    stage: ProgressStage
    current_page: int | None = None
    total_pages: int | None = None
    completed_pages: int | None = None

    @property
    def percentage(self) -> int | None:
        if not self.total_pages or self.completed_pages is None:
            return None
        return min(100, max(0, round(self.completed_pages * 100 / self.total_pages)))


class _OCREventLike(Protocol):
    kind: object
    page_index: int
    total_pages: int


def bundled_css_path() -> Path:
    """Return the stylesheet shipped inside the installed package."""
    return Path(__file__).with_name("style.css")


def sanitize_filename(value: str, fallback: str = "book") -> str:
    """Return a filesystem-friendly title while preserving Unicode letters."""
    cleaned = "".join(character for character in value if character.isalnum() or character in " -_")
    return cleaned.strip().rstrip(".") or fallback


def suggested_output_name(metadata: BookMetadata) -> str:
    title = sanitize_filename(metadata.title)
    if metadata.author and metadata.author != "Unknown":
        author = sanitize_filename(metadata.author, fallback="Unknown")
        return f"{title} - {author}.epub"
    return f"{title}.epub"


def _looks_like_turkish_suffix(fragment: str) -> bool:
    normalized = fragment.casefold()
    return normalized in _TURKISH_EXACT_SUFFIX_FRAGMENTS or normalized.startswith(
        _TURKISH_INLINE_SUFFIX_STARTS
    )


def fix_hyphenation(text: str, language: str = "en") -> tuple[str, int]:
    """Merge OCR line-wrap hyphens while preserving intentional compounds."""
    corrections = 0

    def replace_line_break(match: re.Match[str]) -> str:
        nonlocal corrections
        if match.group(2).islower():
            corrections += 1
            return match.group(1) + match.group(2)
        return match.group(0)

    def replace_inline_break(match: re.Match[str]) -> str:
        nonlocal corrections
        if match.group(2).islower():
            corrections += 1
            return match.group(1) + match.group(2)
        return match.group(0)

    def replace_turkish_inline_break(match: re.Match[str]) -> str:
        nonlocal corrections
        left, right = match.group(1), match.group(2)
        if right.islower() and _looks_like_turkish_suffix(right):
            corrections += 1
            return left + right
        return match.group(0)

    soft_hyphen_pattern = rf"(?<={_LETTER})\u00ad(?={_LETTER})"
    fixed, soft_hyphen_count = re.subn(soft_hyphen_pattern, "", text)
    corrections += soft_hyphen_count

    line_break_pattern = rf"({_LETTER})[{_VISIBLE_HYPHENS}][ \t]*\n\s*({_LETTER})"
    fixed = re.sub(line_break_pattern, replace_line_break, fixed)

    spaced_break_pattern = rf"({_LETTER})[{_VISIBLE_HYPHENS}][ \t]+({_LETTER})"
    fixed = re.sub(spaced_break_pattern, replace_inline_break, fixed)

    if language.casefold().split("-", maxsplit=1)[0] == "tr":
        inline_word_pattern = (
            rf"(?<![\w{_VISIBLE_HYPHENS}])"
            rf"({_LETTER}{{2,}})[{_VISIBLE_HYPHENS}]({_LETTER}{{2,}})"
            rf"(?![\w{_VISIBLE_HYPHENS}])"
        )
        fixed = re.sub(inline_word_pattern, replace_turkish_inline_break, fixed)
    return fixed, corrections


def fix_hyphenation_file(markdown_path: Path, language: str = "en") -> int:
    if not markdown_path.is_file():
        raise ConversionError(f"Generated Markdown was not found: {markdown_path}")
    original = markdown_path.read_text(encoding="utf-8")
    fixed, count = fix_hyphenation(original, language=language)
    markdown_path.write_text(fixed, encoding="utf-8")
    return count


def validate_options(options: ConversionOptions) -> None:
    if not options.pdf_path.is_file():
        raise ConversionError(f"PDF was not found: {options.pdf_path}")
    if options.pdf_path.suffix.lower() != ".pdf":
        raise ConversionError(f"Input must be a PDF file: {options.pdf_path}")
    if options.epub_path.exists() and not options.overwrite:
        raise ConversionError(
            f"Output already exists: {options.epub_path}. Use --overwrite to replace it."
        )
    if options.css_path is not None and not options.css_path.is_file():
        raise ConversionError(f"Stylesheet was not found: {options.css_path}")
    if not 72 <= options.dpi <= 600:
        raise ConversionError("DPI must be between 72 and 600.")


def check_runtime() -> str | None:
    """Validate lightweight runtime requirements and return an optional warning."""
    if shutil.which("pandoc") is None:
        raise ConversionError("Pandoc was not found on PATH. Install Pandoc before converting.")
    try:
        import torch
    except ImportError as error:
        raise ConversionError(
            "PyTorch is not installed. Install a CUDA-compatible build first."
        ) from error

    if not torch.cuda.is_available():
        raise ConversionError(
            "CUDA is not available. Local DeepSeek OCR requires a supported NVIDIA GPU "
            "and a CUDA-enabled PyTorch installation."
        )

    try:
        properties = torch.cuda.get_device_properties(0)
        total_vram = properties.total_memory
        gpu_name = getattr(properties, "name", "Unknown NVIDIA GPU")
        capability = tuple(torch.cuda.get_device_capability(0))
        free_vram, _ = torch.cuda.mem_get_info(0)
        arch_list = list(torch.cuda.get_arch_list())
    except (AttributeError, RuntimeError, TypeError):
        logger.warning("CUDA is available but detailed GPU properties could not be read.")
        return None

    total_vram_gib = total_vram / (1024**3)
    free_vram_gib = free_vram / (1024**3)
    logger.info(
        "CUDA runtime: torch=%s cuda=%s gpu=%s capability=%s total_vram=%.1fGiB "
        "free_vram=%.1fGiB architectures=%s",
        getattr(torch, "__version__", "unknown"),
        getattr(getattr(torch, "version", None), "cuda", "unknown"),
        gpu_name,
        ".".join(str(item) for item in capability),
        total_vram_gib,
        free_vram_gib,
        ",".join(arch_list),
    )

    if capability >= (12, 0) and "sm_120" not in arch_list:
        raise ConversionError(
            "This RTX 50 / Blackwell GPU needs a PyTorch build with sm_120 support. "
            "On Windows, run KURULUM.bat again to install the CUDA 13 build. "
            "Docker and manual installs must select the CUDA 13 PyTorch index."
        )

    try:
        probe = torch.ones(1, device="cuda")
        probe.add_(1)
        torch.cuda.synchronize()
    except RuntimeError as error:
        detail = str(error)
        if "no kernel image" in detail.lower():
            raise ConversionError(
                "The installed PyTorch build cannot run kernels on this NVIDIA GPU. "
                "On Windows, run KURULUM.bat again so the compatible CUDA build can be "
                "installed. Docker and manual installs must select a matching PyTorch build."
            ) from error
        raise ConversionError(f"CUDA could not run a startup test: {detail}") from error

    if total_vram_gib < _MINIMUM_TOTAL_VRAM_GIB:
        raise ConversionError(
            f"The selected NVIDIA GPU ({gpu_name}) has {total_vram_gib:.1f} GB VRAM. "
            "The current unquantized OCR model does not fit reliably in a 6 GB GPU. "
            "Tiny and small reduce per-page work but do not shrink the 6.5 GB model."
        )
    if free_vram_gib < _MINIMUM_START_VRAM_GIB:
        raise ConversionError(
            f"There is not enough free VRAM to load the OCR model ({free_vram_gib:.1f} GB "
            f"available of {total_vram_gib:.1f} GB). Close browsers, games, and other GPU "
            "applications before starting again."
        )
    if free_vram_gib < _MINIMUM_FREE_VRAM_GIB:
        return (
            f"The selected NVIDIA GPU ({gpu_name}) has only {free_vram_gib:.1f} GB of "
            f"{total_vram_gib:.1f} GB VRAM available. Close browsers, games, and other GPU "
            "applications before converting. Tiny or small can reduce per-page memory use."
        )
    return None


def _exception_chain_message(error: Exception) -> str:
    """Return useful messages from wrapped upstream exceptions without a traceback."""
    messages: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen and len(messages) < 6:
        seen.add(id(current))
        message = str(current).strip()
        if message and message not in messages:
            messages.append(message[:1000])
        current = current.__cause__ or current.__context__
    return ": ".join(messages) or type(error).__name__


def _pandoc_command(
    markdown_path: Path,
    epub_path: Path,
    metadata: BookMetadata,
    css_path: Path | None,
) -> list[str]:
    command = [
        "pandoc",
        str(markdown_path),
        "--output",
        str(epub_path),
        "--standalone",
        "--toc",
        "--toc-depth=3",
        f"--resource-path={markdown_path.parent}",
        f"--metadata=title:{metadata.title}",
        f"--metadata=author:{metadata.author}",
        f"--metadata=lang:{metadata.language}",
    ]
    if metadata.publisher:
        command.append(f"--metadata=publisher:{metadata.publisher}")
    if css_path is not None:
        command.append(f"--css={css_path}")
    return command


def create_epub(
    markdown_path: Path,
    epub_path: Path,
    metadata: BookMetadata,
    css_path: Path | None,
) -> None:
    command = _pandoc_command(markdown_path, epub_path, metadata, css_path)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        raise ConversionError(f"Pandoc could not be started: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown Pandoc error"
        raise ConversionError(f"Pandoc failed: {detail}")
    if not epub_path.is_file():
        raise ConversionError("Pandoc reported success but did not create an EPUB file.")


def convert_pdf(
    options: ConversionOptions,
    progress: Callable[[ConversionProgress], None] | None = None,
) -> ConversionResult:
    """Run pdf-craft OCR, repair Markdown, and package the result as EPUB."""
    validate_options(options)
    report = progress or (lambda _progress: None)
    options.epub_path.parent.mkdir(parents=True, exist_ok=True)
    options.models_dir.mkdir(parents=True, exist_ok=True)
    if options.work_parent is not None:
        options.work_parent.mkdir(parents=True, exist_ok=True)

    work_dir = Path(
        tempfile.mkdtemp(
            prefix=f"{sanitize_filename(options.pdf_path.stem)}-",
            dir=options.work_parent,
        )
    )
    markdown_path = work_dir / "book.md"
    assets_path = work_dir / "assets"
    start = time.monotonic()

    try:
        copy_cache = configure_huggingface_cache(options.models_dir)
        logger.info(
            "Conversion started: pdf=%s output=%s ocr_size=%s dpi=%s models=%s "
            "windows_copy_cache=%s",
            options.pdf_path,
            options.epub_path,
            options.ocr_size,
            options.dpi,
            options.models_dir,
            copy_cache,
        )
        report(ConversionProgress("Checking and downloading OCR models", "models"))
        from pdf_craft import transform_markdown

        # Do not call pdf-craft's predownload_models() here. Its current local backend
        # deliberately uses force_download=True, which can download the 6.5 GB model again
        # after every retry. Transformers downloads missing files during the conversion and
        # reuses the Hugging Face cache on later runs.
        report(ConversionProgress("Converting PDF to Markdown with OCR", "ocr"))

        def on_ocr_event(event: _OCREventLike) -> None:
            kind = getattr(getattr(event, "kind", None), "name", "")
            if kind not in {"START", "RENDERED", "COMPLETE", "FAILED", "SKIP", "IGNORE"}:
                return
            current_page = event.page_index
            total_pages = event.total_pages
            logger.info("OCR event: kind=%s page=%s total=%s", kind, current_page, total_pages)
            if kind == "START":
                message = "Rendering PDF page"
                completed_pages = max(0, current_page - 1)
            elif kind == "RENDERED":
                message = "Loading OCR model and processing PDF page"
                completed_pages = max(0, current_page - 1)
            else:
                message = "Completed PDF page"
                completed_pages = current_page
            report(
                ConversionProgress(
                    message=message,
                    stage="ocr",
                    current_page=current_page,
                    total_pages=total_pages,
                    completed_pages=completed_pages,
                )
            )

        transform_markdown(
            pdf_path=str(options.pdf_path),
            markdown_path=str(markdown_path),
            markdown_assets_path=str(assets_path),
            analysing_path=str(work_dir / "analysis"),
            ocr_size=options.ocr_size,
            models_cache_path=str(options.models_dir),
            dpi=options.dpi,
            on_ocr_event=on_ocr_event,
        )

        report(ConversionProgress("Repairing line-end hyphenation", "cleanup"))
        fixes = fix_hyphenation_file(markdown_path, language=options.metadata.language)
        report(ConversionProgress("Building EPUB with Pandoc", "epub"))
        create_epub(markdown_path, options.epub_path, options.metadata, options.css_path)
        return ConversionResult(
            epub_path=options.epub_path,
            work_dir=work_dir,
            elapsed_seconds=time.monotonic() - start,
            hyphenation_fixes=fixes,
            intermediates_kept=options.keep_intermediates,
        )
    except ConversionError:
        logger.exception("Conversion failed with a known error.")
        raise
    except Exception as error:
        logger.exception("Conversion failed in the OCR pipeline.")
        raise ConversionError(f"Conversion failed: {_exception_chain_message(error)}") from error
    finally:
        if not options.keep_intermediates:
            shutil.rmtree(work_dir, ignore_errors=True)
