"""Testable conversion pipeline built around pdf-craft and Pandoc."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

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
        total_vram = torch.cuda.get_device_properties(0).total_memory
    except (AttributeError, RuntimeError):
        return None
    total_vram_gib = total_vram / (1024**3)
    if total_vram_gib < 16:
        return (
            f"The selected NVIDIA GPU has {total_vram_gib:.1f} GB VRAM; pdf-craft "
            "recommends at least 16 GB. Close other GPU applications and start with "
            "the tiny or small OCR setting."
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
        report(ConversionProgress("Checking and downloading OCR models", "models"))
        from pdf_craft import transform_markdown

        # Do not call pdf-craft's predownload_models() here. Its current local backend
        # deliberately uses force_download=True, which can download the 6.5 GB model again
        # after every retry. Transformers downloads missing files during the conversion and
        # reuses the Hugging Face cache on later runs.
        report(ConversionProgress("Converting PDF to Markdown with OCR", "ocr"))

        def on_ocr_event(event: _OCREventLike) -> None:
            kind = getattr(getattr(event, "kind", None), "name", "")
            if kind not in {"START", "COMPLETE", "FAILED", "SKIP", "IGNORE"}:
                return
            current_page = event.page_index
            total_pages = event.total_pages
            page_finished = kind != "START"
            report(
                ConversionProgress(
                    message="Completed PDF page" if page_finished else "Reading PDF page",
                    stage="ocr",
                    current_page=current_page,
                    total_pages=total_pages,
                    completed_pages=current_page if page_finished else max(0, current_page - 1),
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
        raise
    except Exception as error:
        raise ConversionError(f"Conversion failed: {_exception_chain_message(error)}") from error
    finally:
        if not options.keep_intermediates:
            shutil.rmtree(work_dir, ignore_errors=True)
