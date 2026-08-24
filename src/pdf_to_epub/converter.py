"""Testable conversion pipeline built around pdf-craft and Pandoc."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Literal, Protocol

from pdf_to_epub.model_cache import configure_huggingface_cache
from pdf_to_epub.platform_support import desktop_platform, macos_ocr_unavailable, repair_action

logger = logging.getLogger(__name__)

_MINIMUM_TOTAL_VRAM_GIB = 7.0
_MINIMUM_START_VRAM_GIB = 5.5
_MINIMUM_FREE_VRAM_GIB = 6.5
_OUTPUT_EXTENSIONS = {"epub": ".epub", "markdown": ".md", "mobi": ".mobi"}
_PIPE_TABLE_PATTERN = re.compile(r"(?:^[ \t]*\|.*\|[ \t]*$\n?){2,}", re.MULTILINE)
_HTML_TABLE_PATTERN = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
_HTML_CELL_PATTERN = re.compile(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", re.IGNORECASE | re.DOTALL)
_DIALOGUE_BOUNDARY_PATTERN = re.compile(r'(?P<closing>[.!?…]["”»])[ \t]*(?P<opening>["“«])')
_EXPLICIT_CHAPTER_HEADING_PATTERN = re.compile(
    r"(?:"
    r"(?:bölüm|kısım|kitap|chapter|part|book)\s+(?:\d{1,4}|[ivxlcdm]+)"
    r"|(?:\d{1,4}|[ivxlcdm]+)[.\-:]?\s+(?:bölüm|kısım|kitap|chapter|part|book)"
    r")",
    re.IGNORECASE,
)

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


OutputFormat = Literal["epub", "markdown", "mobi"]
AcceleratorBackend = Literal["cuda", "rocm"]


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

    @property
    def output_path(self) -> Path:
        """Return the selected output path while preserving the historical field name."""
        return self.epub_path

    @property
    def output_format(self) -> OutputFormat:
        return output_format_from_path(self.epub_path)


@dataclass(frozen=True)
class ConversionResult:
    epub_path: Path
    work_dir: Path
    elapsed_seconds: float
    hyphenation_fixes: int
    intermediates_kept: bool

    @property
    def output_path(self) -> Path:
        """Return the generated file while preserving the historical field name."""
        return self.epub_path

    @property
    def output_format(self) -> OutputFormat:
        return output_format_from_path(self.epub_path)


ProgressStage = Literal["models", "ocr", "cleanup", "epub"]


@dataclass(frozen=True)
class ConversionProgress:
    """Structured conversion status suitable for a CLI or desktop progress bar."""

    message: str
    stage: ProgressStage
    current_page: int | None = None
    total_pages: int | None = None
    completed_pages: int | None = None
    estimated_remaining_seconds: float | None = None

    @property
    def percentage(self) -> int | None:
        if not self.total_pages or self.completed_pages is None:
            return None
        return min(100, max(0, round(self.completed_pages * 100 / self.total_pages)))


class ConversionPauseController:
    """Thread-safe cooperative pause gate used by pdf-craft's abort checkpoints."""

    def __init__(self) -> None:
        self._running = threading.Event()
        self._running.set()
        self._lock = threading.Lock()
        self._paused_at: float | None = None
        self._paused_seconds = 0.0

    @property
    def is_paused(self) -> bool:
        return not self._running.is_set()

    @property
    def paused_seconds(self) -> float:
        with self._lock:
            current_pause = 0.0
            if self._paused_at is not None:
                current_pause = time.monotonic() - self._paused_at
            return self._paused_seconds + current_pause

    def pause(self) -> bool:
        """Pause at the next cooperative checkpoint; return whether state changed."""
        with self._lock:
            if self._paused_at is not None:
                return False
            self._paused_at = time.monotonic()
            self._running.clear()
            return True

    def resume(self) -> bool:
        """Release a paused conversion; return whether state changed."""
        with self._lock:
            if self._paused_at is None:
                return False
            self._paused_seconds += time.monotonic() - self._paused_at
            self._paused_at = None
            self._running.set()
            return True

    def wait_if_paused(self) -> bool:
        """Block the OCR worker while paused and always report 'not aborted' upstream."""
        self._running.wait()
        return False


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


def output_format_from_path(path: Path) -> OutputFormat:
    """Infer a supported output format from a destination suffix."""
    suffix = path.suffix.casefold()
    for output_format, extension in _OUTPUT_EXTENSIONS.items():
        if suffix == extension:
            return output_format  # type: ignore[return-value]
    raise ConversionError(
        f"Output must use one of these extensions: {', '.join(_OUTPUT_EXTENSIONS.values())}."
    )


def suggested_output_name(metadata: BookMetadata, output_format: OutputFormat = "epub") -> str:
    title = sanitize_filename(metadata.title)
    extension = _OUTPUT_EXTENSIONS[output_format]
    if metadata.author and metadata.author != "Unknown":
        author = sanitize_filename(metadata.author, fallback="Unknown")
        return f"{title} - {author}{extension}"
    return f"{title}{extension}"


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

    line_break_pattern = rf"({_LETTER})[{_VISIBLE_HYPHENS}][^\S\r\n]*\r?\n[^\S\r\n]*({_LETTER})"
    fixed = re.sub(line_break_pattern, replace_line_break, fixed)

    spaced_break_pattern = rf"({_LETTER})[{_VISIBLE_HYPHENS}][^\S\r\n]+({_LETTER})"
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


def _plain_table_cell(cell: str) -> str:
    with_breaks = re.sub(r"<br\s*/?>", "\n", cell, flags=re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", "", with_breaks)
    return unescape(without_tags).strip()


def _is_placeholder_cell(cell: str) -> bool:
    return not cell.strip() or _plain_table_cell(cell).casefold() == "none"


def _looks_like_misclassified_prose_table(cells: list[str]) -> bool:
    """Detect the narrow OCR failure that puts one paragraph among empty/None cells."""
    if len(cells) < 3:
        return False
    placeholders = sum(_is_placeholder_cell(cell) for cell in cells)
    meaningful = [_plain_table_cell(cell) for cell in cells if not _is_placeholder_cell(cell)]
    if placeholders < 2 or placeholders * 2 < len(cells) or not meaningful:
        return False
    longest_word_count = max(len(re.findall(r"\w+", cell, flags=re.UNICODE)) for cell in meaningful)
    return longest_word_count >= 8


def _pipe_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_pipe_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def cleanup_ocr_tables(text: str) -> tuple[str, int]:
    """Flatten obvious prose-as-table OCR mistakes and remove literal None placeholders."""
    fixes = 0

    def replace_pipe_table(match: re.Match[str]) -> str:
        nonlocal fixes
        block = match.group(0)
        lines = block.rstrip("\n").splitlines()
        if len(lines) < 2 or not _is_pipe_separator(_pipe_table_cells(lines[1])):
            return block
        cells = [
            cell
            for index, line in enumerate(lines)
            if index != 1
            for cell in _pipe_table_cells(line)
        ]
        if _looks_like_misclassified_prose_table(cells):
            fixes += 1
            paragraphs = [
                _plain_table_cell(cell) for cell in cells if not _is_placeholder_cell(cell)
            ]
            suffix = "\n" if block.endswith("\n") else ""
            return "\n\n".join(paragraphs) + suffix
        return block

    def replace_html_table(match: re.Match[str]) -> str:
        nonlocal fixes
        block = match.group(0)
        raw_cells = _HTML_CELL_PATTERN.findall(block)
        if _looks_like_misclassified_prose_table(raw_cells):
            fixes += 1
            paragraphs = [
                _plain_table_cell(cell) for cell in raw_cells if not _is_placeholder_cell(cell)
            ]
            return "\n\n".join(paragraphs)
        return block

    cleaned = _PIPE_TABLE_PATTERN.sub(replace_pipe_table, text)
    cleaned = _HTML_TABLE_PATTERN.sub(replace_html_table, cleaned)
    return cleaned, fixes


def cleanup_ocr_tables_file(markdown_path: Path) -> int:
    if not markdown_path.is_file():
        raise ConversionError(f"Generated Markdown was not found: {markdown_path}")
    original = markdown_path.read_text(encoding="utf-8")
    fixed, count = cleanup_ocr_tables(original)
    markdown_path.write_text(fixed, encoding="utf-8")
    return count


def _is_hallucinated_number_sequence(block: str) -> bool:
    """Recognize long, near-sequential number-only output hallucinated on blank pages."""
    if re.sub(r"[\d\s.,;:(){}\[\]\-–—]+", "", block):
        return False
    numbers = [int(value) for value in re.findall(r"\d{1,7}", block)]
    if len(numbers) < 25:
        return False
    valid_transitions = sum(
        current == previous + 1 or (current == 1 and previous >= 20)
        for previous, current in zip(numbers, numbers[1:], strict=False)
    )
    return valid_transitions / (len(numbers) - 1) >= 0.9


def cleanup_ocr_structure(text: str) -> tuple[str, int, int, int]:
    """Repair conservative paragraph/heading issues and discard numeric OCR hallucinations."""
    dialogue_fixes = 0
    heading_fixes = 0
    hallucination_fixes = 0

    def split_dialogue(match: re.Match[str]) -> str:
        nonlocal dialogue_fixes
        dialogue_fixes += 1
        return f"{match.group('closing')}\n\n{match.group('opening')}"

    fixed = _DIALOGUE_BOUNDARY_PATTERN.sub(split_dialogue, text)
    parts = re.split(r"(\n{2,})", fixed)
    for index in range(0, len(parts), 2):
        block = parts[index]
        stripped = block.strip()
        if not stripped:
            continue
        if _is_hallucinated_number_sequence(stripped):
            parts[index] = ""
            hallucination_fixes += 1
            continue
        if (
            "\n" not in stripped
            and not stripped.startswith("#")
            and _EXPLICIT_CHAPTER_HEADING_PATTERN.fullmatch(stripped)
        ):
            leading = block[: len(block) - len(block.lstrip())]
            trailing = block[len(block.rstrip()) :]
            parts[index] = f"{leading}## {stripped}{trailing}"
            heading_fixes += 1

    cleaned = "".join(parts)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip("\n")
    if text.endswith("\n"):
        cleaned += "\n"
    return cleaned, dialogue_fixes, heading_fixes, hallucination_fixes


def cleanup_ocr_structure_file(markdown_path: Path) -> tuple[int, int, int]:
    if not markdown_path.is_file():
        raise ConversionError(f"Generated Markdown was not found: {markdown_path}")
    original = markdown_path.read_text(encoding="utf-8")
    fixed, dialogue_fixes, heading_fixes, hallucination_fixes = cleanup_ocr_structure(original)
    markdown_path.write_text(fixed, encoding="utf-8")
    return dialogue_fixes, heading_fixes, hallucination_fixes


def estimate_remaining_seconds(
    *, elapsed_seconds: float, completed_pages: int, total_pages: int
) -> float | None:
    """Estimate remaining OCR time after enough completed pages to reduce first-page noise."""
    if elapsed_seconds < 0 or completed_pages < 3 or total_pages <= completed_pages:
        return None
    return elapsed_seconds * (total_pages - completed_pages) / completed_pages


def validate_options(options: ConversionOptions) -> None:
    if not options.pdf_path.is_file():
        raise ConversionError(f"PDF was not found: {options.pdf_path}")
    if options.pdf_path.suffix.lower() != ".pdf":
        raise ConversionError(f"Input must be a PDF file: {options.pdf_path}")
    output_format = output_format_from_path(options.output_path)
    if options.output_path.exists() and not options.overwrite:
        raise ConversionError(
            f"Output already exists: {options.output_path}. Use --overwrite to replace it."
        )
    if output_format == "markdown":
        assets_output = markdown_assets_output_path(options.output_path)
        if assets_output.exists() and not options.overwrite:
            raise ConversionError(
                f"Markdown assets already exist: {assets_output}. Use --overwrite to replace them."
            )
    if options.css_path is not None and not options.css_path.is_file():
        raise ConversionError(f"Stylesheet was not found: {options.css_path}")
    if not 72 <= options.dpi <= 600:
        raise ConversionError("DPI must be between 72 and 600.")


def find_ebook_convert() -> str | None:
    """Locate Calibre's MOBI converter on PATH or in standard Windows locations."""
    command = shutil.which("ebook-convert")
    if command:
        return command
    if sys.platform != "win32":
        return None
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if not root:
            continue
        candidate = Path(root) / "Calibre2" / "ebook-convert.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def accelerator_backend(torch_module: object) -> AcceleratorBackend:
    """Identify CUDA or ROCm without assuming the torch.cuda namespace means NVIDIA."""
    version = getattr(torch_module, "version", None)
    return "rocm" if getattr(version, "hip", None) else "cuda"


def check_runtime(output_format: OutputFormat = "epub") -> str | None:
    """Validate lightweight runtime requirements and return an optional warning."""
    if output_format in {"epub", "mobi"} and shutil.which("pandoc") is None:
        raise ConversionError("Pandoc was not found on PATH. Install Pandoc before converting.")
    if output_format == "mobi" and find_ebook_convert() is None:
        raise ConversionError(
            "Calibre ebook-convert was not found. Install Calibre or repair the application "
            "to enable MOBI output."
        )
    try:
        import torch
    except ImportError as error:
        raise ConversionError(
            "PyTorch is not installed. Install a CUDA/ROCm-compatible build first."
        ) from error

    if not torch.cuda.is_available():
        if desktop_platform() == "macos":
            raise ConversionError(macos_ocr_unavailable())
        raise ConversionError(
            "CUDA/ROCm is not available. Local DeepSeek OCR requires a supported NVIDIA CUDA "
            "or AMD ROCm GPU and a matching PyTorch installation."
        )

    backend = accelerator_backend(torch)
    try:
        properties = torch.cuda.get_device_properties(0)
        total_vram = properties.total_memory
        gpu_name = getattr(properties, "name", "Unknown GPU")
        free_vram, _ = torch.cuda.mem_get_info(0)
    except (AttributeError, RuntimeError, TypeError):
        logger.warning("GPU acceleration is available but VRAM properties could not be read.")
        properties = None
        total_vram = 0
        free_vram = 0
        gpu_name = "Unknown GPU"

    try:
        capability = tuple(torch.cuda.get_device_capability(0))
    except (AttributeError, RuntimeError, TypeError):
        capability = ()
    try:
        arch_list = list(torch.cuda.get_arch_list())
    except (AttributeError, RuntimeError, TypeError):
        arch_list = []

    total_vram_gib = total_vram / (1024**3)
    free_vram_gib = free_vram / (1024**3)
    logger.info(
        "GPU runtime: backend=%s torch=%s cuda=%s hip=%s gpu=%s capability=%s "
        "total_vram=%.1fGiB free_vram=%.1fGiB architectures=%s",
        backend,
        getattr(torch, "__version__", "unknown"),
        getattr(getattr(torch, "version", None), "cuda", "unknown"),
        getattr(getattr(torch, "version", None), "hip", "none"),
        gpu_name,
        ".".join(str(item) for item in capability) or "unknown",
        total_vram_gib,
        free_vram_gib,
        ",".join(arch_list),
    )

    if backend == "cuda" and capability >= (12, 0) and "sm_120" not in arch_list:
        raise ConversionError(
            "This RTX 50 / Blackwell GPU needs a PyTorch build with sm_120 support. "
            f"{repair_action()} Docker and manual installs must select the CUDA 13 "
            "PyTorch index."
        )

    try:
        probe = torch.ones(1, device="cuda")
        probe.add_(1)
        torch.cuda.synchronize()
    except RuntimeError as error:
        detail = str(error)
        if "no kernel image" in detail.lower():
            raise ConversionError(
                "The installed PyTorch build cannot run kernels on this GPU. "
                f"{repair_action()} Docker and manual installs must select a compatible "
                "NVIDIA CUDA or AMD ROCm build."
            ) from error
        raise ConversionError(f"GPU acceleration could not run a startup test: {detail}") from error

    if properties is None:
        return None
    if total_vram_gib < _MINIMUM_TOTAL_VRAM_GIB:
        raise ConversionError(
            f"The selected GPU ({gpu_name}) has {total_vram_gib:.1f} GB VRAM. "
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
            f"The selected GPU ({gpu_name}) has only {free_vram_gib:.1f} GB of "
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
    cover_path: Path | None = None,
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
    if cover_path is not None:
        command.append(f"--epub-cover-image={cover_path}")
    return command


def create_epub(
    markdown_path: Path,
    epub_path: Path,
    metadata: BookMetadata,
    css_path: Path | None,
    cover_path: Path | None = None,
) -> None:
    command = _pandoc_command(markdown_path, epub_path, metadata, css_path, cover_path)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        raise ConversionError(f"Pandoc could not be started: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown Pandoc error"
        raise ConversionError(f"Pandoc failed: {detail}")
    if not epub_path.is_file():
        raise ConversionError("Pandoc reported success but did not create an EPUB file.")


def markdown_assets_output_path(markdown_output: Path) -> Path:
    """Return the sibling directory used for images referenced by exported Markdown."""
    return markdown_output.with_name(f"{markdown_output.stem}_assets")


def export_markdown(
    markdown_path: Path,
    assets_path: Path,
    output_path: Path,
    *,
    overwrite: bool,
) -> None:
    """Publish cleaned Markdown and its OCR image assets to the selected destination."""
    content = markdown_path.read_text(encoding="utf-8")
    if assets_path.is_dir():
        output_assets = markdown_assets_output_path(output_path)
        if output_assets.exists():
            if not overwrite:
                raise ConversionError(f"Markdown assets already exist: {output_assets}")
            shutil.rmtree(output_assets)
        shutil.copytree(assets_path, output_assets)
        content = content.replace("assets/", f"{output_assets.name}/")
    output_path.write_text(content, encoding="utf-8")


def create_mobi(
    markdown_path: Path,
    mobi_path: Path,
    metadata: BookMetadata,
    css_path: Path | None,
    cover_path: Path | None = None,
) -> None:
    """Build an EPUB with Pandoc and convert it to legacy MOBI with Calibre."""
    ebook_convert = find_ebook_convert()
    if ebook_convert is None:
        raise ConversionError(
            "Calibre ebook-convert was not found. Use Maintenance Center > Repair to enable "
            "MOBI output."
        )
    intermediate_epub = markdown_path.with_name("mobi-source.epub")
    create_epub(markdown_path, intermediate_epub, metadata, css_path, cover_path)
    try:
        result = subprocess.run(
            [ebook_convert, str(intermediate_epub), str(mobi_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ConversionError(f"Calibre ebook-convert could not be started: {error}") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown Calibre error"
        raise ConversionError(f"Calibre MOBI conversion failed: {detail}")
    if not mobi_path.is_file():
        raise ConversionError("Calibre reported success but did not create a MOBI file.")


def convert_pdf(
    options: ConversionOptions,
    progress: Callable[[ConversionProgress], None] | None = None,
    pause_controller: ConversionPauseController | None = None,
) -> ConversionResult:
    """Run pdf-craft OCR, repair Markdown, and publish the selected e-book format."""
    validate_options(options)
    report = progress or (lambda _progress: None)
    pause = pause_controller or ConversionPauseController()
    options.output_path.parent.mkdir(parents=True, exist_ok=True)
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
    analysis_path = work_dir / "analysis"
    cover_path = analysis_path / "cover.png"
    start = time.monotonic()
    ocr_started_at: float | None = None

    try:
        copy_cache = configure_huggingface_cache(options.models_dir)
        logger.info(
            "Conversion started: pdf=%s output=%s ocr_size=%s dpi=%s models=%s "
            "windows_copy_cache=%s",
            options.pdf_path,
            options.output_path,
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
            nonlocal ocr_started_at
            kind = getattr(getattr(event, "kind", None), "name", "")
            if kind not in {"START", "RENDERED", "COMPLETE", "FAILED", "SKIP", "IGNORE"}:
                return
            now = time.monotonic()
            if ocr_started_at is None:
                ocr_started_at = now
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
            remaining_seconds = estimate_remaining_seconds(
                elapsed_seconds=max(0.0, now - ocr_started_at - pause.paused_seconds),
                completed_pages=completed_pages,
                total_pages=total_pages,
            )
            report(
                ConversionProgress(
                    message=message,
                    stage="ocr",
                    current_page=current_page,
                    total_pages=total_pages,
                    completed_pages=completed_pages,
                    estimated_remaining_seconds=remaining_seconds,
                )
            )

        transform_markdown(
            pdf_path=str(options.pdf_path),
            markdown_path=str(markdown_path),
            markdown_assets_path=str(assets_path),
            analysing_path=str(analysis_path),
            ocr_size=options.ocr_size,
            models_cache_path=str(options.models_dir),
            dpi=options.dpi,
            includes_cover=options.output_format in {"epub", "mobi"},
            aborted=pause.wait_if_paused,
            on_ocr_event=on_ocr_event,
        )

        pause.wait_if_paused()
        report(ConversionProgress("Repairing line-end hyphenation", "cleanup"))
        fixes = fix_hyphenation_file(markdown_path, language=options.metadata.language)
        table_fixes = cleanup_ocr_tables_file(markdown_path)
        dialogue_fixes, heading_fixes, hallucination_fixes = cleanup_ocr_structure_file(
            markdown_path
        )
        logger.info(
            "OCR cleanup: hyphenation_fixes=%s table_fixes=%s dialogue_fixes=%s "
            "heading_fixes=%s hallucination_blocks_removed=%s",
            fixes,
            table_fixes,
            dialogue_fixes,
            heading_fixes,
            hallucination_fixes,
        )
        ebook_cover = cover_path if cover_path.is_file() else None
        if options.output_format in {"epub", "mobi"}:
            report(ConversionProgress("Embedding full-page cover", "epub"))
            if ebook_cover is None:
                logger.warning("The OCR pipeline did not produce a dedicated first-page cover.")
        if options.output_format == "markdown":
            pause.wait_if_paused()
            report(ConversionProgress("Writing Markdown output", "epub"))
            export_markdown(
                markdown_path,
                assets_path,
                options.output_path,
                overwrite=options.overwrite,
            )
        elif options.output_format == "mobi":
            pause.wait_if_paused()
            report(ConversionProgress("Building MOBI with Calibre", "epub"))
            create_mobi(
                markdown_path,
                options.output_path,
                options.metadata,
                options.css_path,
                ebook_cover,
            )
        else:
            pause.wait_if_paused()
            report(ConversionProgress("Building EPUB with Pandoc", "epub"))
            create_epub(
                markdown_path,
                options.output_path,
                options.metadata,
                options.css_path,
                ebook_cover,
            )
        return ConversionResult(
            epub_path=options.output_path,
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
