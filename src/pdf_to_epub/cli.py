"""Command-line interface for PDF to EPUB OCR."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from platformdirs import user_cache_path

from pdf_to_epub import __version__
from pdf_to_epub.converter import (
    BookMetadata,
    ConversionError,
    ConversionOptions,
    ConversionProgress,
    OutputFormat,
    bundled_css_path,
    check_runtime,
    convert_pdf,
    output_format_from_path,
    suggested_output_name,
)
from pdf_to_epub.diagnostics import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf-to-epub-ocr",
        description="Convert scanned PDF books into EPUB, Markdown, or MOBI with local OCR.",
    )
    parser.add_argument("pdf", nargs="?", type=Path, help="PDF file to convert")
    parser.add_argument("-o", "--output", type=Path, help="output path (.epub, .md, or .mobi)")
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("epub", "markdown", "mobi"),
        help="output format; inferred from --output when omitted",
    )
    parser.add_argument("--title", help="book title (defaults to the PDF filename)")
    parser.add_argument("--author", default="Unknown", help="author name (default: Unknown)")
    parser.add_argument("--publisher", default="", help="publisher metadata")
    parser.add_argument("--lang", default="en", help="EPUB language tag (default: en)")
    parser.add_argument(
        "--ocr-size",
        choices=("tiny", "small", "base", "large", "gundam"),
        default="gundam",
        help="OCR model size (default: gundam)",
    )
    parser.add_argument("--dpi", type=int, default=300, help="render DPI, 72-600 (default: 300)")
    style_group = parser.add_mutually_exclusive_group()
    style_group.add_argument("--css", type=Path, help="custom EPUB stylesheet")
    style_group.add_argument("--no-css", action="store_true", help="do not embed a stylesheet")
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=user_cache_path("pdf-to-epub-ocr") / "models",
        help="OCR model cache directory",
    )
    parser.add_argument("--work-dir", type=Path, help="parent directory for intermediate files")
    parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="keep generated Markdown, assets, and analysis files",
    )
    parser.add_argument("--overwrite", action="store_true", help="replace existing output")
    parser.add_argument("-y", "--yes", action="store_true", help="skip interactive confirmation")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _select_pdf(input_dir: Path) -> Path:
    input_dir.mkdir(parents=True, exist_ok=True)
    candidates = sorted(input_dir.glob("*.pdf"))
    if not candidates:
        raise ConversionError(f"No PDF files were found in {input_dir}")
    if len(candidates) == 1:
        return candidates[0]

    print("Available PDF files:")
    for index, candidate in enumerate(candidates, start=1):
        print(f"  {index}. {candidate.name}")
    while True:
        try:
            selection = int(input(f"Select a PDF (1-{len(candidates)}): ")) - 1
            if 0 <= selection < len(candidates):
                return candidates[selection]
        except ValueError:
            pass
        print("Invalid selection; try again.", file=sys.stderr)


def _interactive_metadata(pdf_path: Path, args: argparse.Namespace) -> BookMetadata:
    default_title = args.title or pdf_path.stem
    title = input(f"Title [{default_title}]: ").strip() or default_title
    author = input(f"Author [{args.author}]: ").strip() or args.author
    publisher = input("Publisher [none]: ").strip() or args.publisher
    language = input(f"Language [{args.lang}]: ").strip() or args.lang
    return BookMetadata(title=title, author=author, publisher=publisher, language=language)


def _progress(progress: ConversionProgress) -> None:
    if progress.current_page is not None and progress.total_pages is not None:
        percentage = progress.percentage or 0
        print(f"[+] Page {progress.current_page}/{progress.total_pages} ({percentage}%)")
    else:
        print(f"[+] {progress.message}...")


def _output_selection(
    output: Path | None,
    requested_format: OutputFormat | None,
    metadata: BookMetadata,
) -> tuple[Path, OutputFormat]:
    """Resolve a friendly destination and reject contradictory format choices."""
    if output is None:
        output_format: OutputFormat = requested_format or "epub"
        return Path.cwd() / "output" / suggested_output_name(metadata, output_format), output_format

    if output.suffix:
        inferred_format = output_format_from_path(output)
        if requested_format is not None and requested_format != inferred_format:
            raise ConversionError(
                f"--format {requested_format} does not match the output extension {output.suffix}."
            )
        return output, inferred_format

    output_format = requested_format or "epub"
    extension = ".md" if output_format == "markdown" else f".{output_format}"
    return output.with_suffix(extension), output_format


def main(argv: list[str] | None = None) -> int:
    log_path = configure_logging()
    logger.info("CLI application starting.")
    parser = build_parser()
    args = parser.parse_args(argv)
    interactive = args.pdf is None

    try:
        pdf_path = (_select_pdf(Path.cwd() / "input") if interactive else args.pdf).resolve()
        metadata = (
            _interactive_metadata(pdf_path, args)
            if interactive
            else BookMetadata(
                title=args.title or pdf_path.stem,
                author=args.author,
                publisher=args.publisher,
                language=args.lang,
            )
        )
        output_path, output_format = _output_selection(
            args.output,
            args.output_format,
            metadata,
        )
        output_path = output_path.resolve()
        css_path = None if args.no_css else (args.css.resolve() if args.css else bundled_css_path())

        print(f"Input : {pdf_path}")
        print(f"Output: {output_path}")
        print(f"OCR   : {args.ocr_size} at {args.dpi} DPI")
        if interactive and not args.yes:
            input("Press Enter to start (Ctrl+C to cancel)...")

        warning = check_runtime(output_format)
        if warning:
            print(f"[WARNING] {warning}", file=sys.stderr)

        result = convert_pdf(
            ConversionOptions(
                pdf_path=pdf_path,
                epub_path=output_path,
                metadata=metadata,
                models_dir=args.models_dir.resolve(),
                work_parent=args.work_dir.resolve() if args.work_dir else None,
                css_path=css_path,
                ocr_size=args.ocr_size,
                dpi=args.dpi,
                keep_intermediates=args.keep_intermediates,
                overwrite=args.overwrite,
            ),
            progress=_progress,
        )
    except (ConversionError, OSError) as error:
        logger.exception("CLI conversion failed.")
        print(f"[ERROR] {error}", file=sys.stderr)
        print(f"[ERROR] Diagnostic log: {log_path}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130

    print(f"[OK] {result.output_format.upper()} created: {result.output_path}")
    print(f"[OK] Hyphenation corrections: {result.hyphenation_fixes}")
    print(f"[OK] Elapsed time: {result.elapsed_seconds:.1f} seconds")
    if result.intermediates_kept:
        print(f"[OK] Intermediate files: {result.work_dir}")
    return 0
