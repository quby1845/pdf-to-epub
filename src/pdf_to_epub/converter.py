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


def fix_hyphenation(text: str) -> tuple[str, int]:
    """Merge common OCR line-wrap hyphens when the continuation is lowercase."""
    corrections = 0

    def replace_line_break(match: re.Match[str]) -> str:
        nonlocal corrections
        if match.group(3).islower():
            corrections += 1
            return match.group(1) + match.group(3)
        return match.group(0)

    def replace_inline_break(match: re.Match[str]) -> str:
        nonlocal corrections
        if match.group(2).islower():
            corrections += 1
            return match.group(1) + match.group(2)
        return match.group(0)

    fixed = re.sub(r"(\w)-\n(\s*)(\w)", replace_line_break, text)
    fixed = re.sub(r"(\w)- (\w)", replace_inline_break, fixed)
    return fixed, corrections


def fix_hyphenation_file(markdown_path: Path) -> int:
    if not markdown_path.is_file():
        raise ConversionError(f"Generated Markdown was not found: {markdown_path}")
    original = markdown_path.read_text(encoding="utf-8")
    fixed, count = fix_hyphenation(original)
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
        return "CUDA is not available; conversion may be unsupported or extremely slow."
    return None


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
    progress: Callable[[str], None] | None = None,
) -> ConversionResult:
    """Run pdf-craft OCR, repair Markdown, and package the result as EPUB."""
    validate_options(options)
    report = progress or (lambda _message: None)
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
        report("Checking and downloading OCR models")
        from pdf_craft import predownload_models, transform_markdown

        predownload_models(models_cache_path=str(options.models_dir))
        report("Converting PDF to Markdown with OCR")
        transform_markdown(
            pdf_path=str(options.pdf_path),
            markdown_path=str(markdown_path),
            markdown_assets_path=str(assets_path),
            analysing_path=str(work_dir / "analysis"),
            ocr_size=options.ocr_size,
            models_cache_path=str(options.models_dir),
            dpi=options.dpi,
        )

        report("Repairing line-end hyphenation")
        fixes = fix_hyphenation_file(markdown_path)
        report("Building EPUB with Pandoc")
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
        raise ConversionError(f"Conversion failed: {error}") from error
    finally:
        if not options.keep_intermediates:
            shutil.rmtree(work_dir, ignore_errors=True)
