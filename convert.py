"""
PDF to EPUB Converter
=====================
Converts PDF files to high-quality EPUB format using AI-powered OCR.

Usage:
    python convert.py                          # interactive mode
    python convert.py input.pdf                # single file
    python convert.py input.pdf -o book.epub   # specify output name
    python convert.py input.pdf --title "Book Title" --author "Author" --publisher "Publisher"

Requirements:
    - NVIDIA GPU (min. 8GB VRAM)
    - PyTorch (with CUDA support)
    - pdf-craft
    - pandoc
    - poppler
"""

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


# ============================================================
# Constants
# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
MODELS_DIR = SCRIPT_DIR / "models"
TEMP_DIR = SCRIPT_DIR / "temp"
INPUT_DIR = SCRIPT_DIR / "input"
OUTPUT_DIR = SCRIPT_DIR / "output"


# ============================================================
# Helpers
# ============================================================
def print_header(text: str) -> None:
    """Print a colored section header."""
    border = "=" * 50
    print(f"\n\033[96m{border}\033[0m")
    print(f"\033[96m  {text}\033[0m")
    print(f"\033[96m{border}\033[0m\n")


def print_step(step: int, total: int, text: str) -> None:
    """Print a numbered step line."""
    print(f"\033[92m[{step}/{total}]\033[0m {text}")


def print_warn(text: str) -> None:
    """Print a warning message."""
    print(f"\033[93m[WARN]\033[0m {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"\033[91m[ERROR]\033[0m {text}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"\033[92m[OK]\033[0m {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"\033[90m     {text}\033[0m")


def check_cuda() -> bool:
    """Check CUDA availability."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print_success(f"CUDA active — {gpu_name} ({vram:.1f} GB VRAM)")
            return True
        else:
            print_warn("CUDA not found! Processing will continue on CPU (very slow).")
            return False
    except ImportError:
        print_error("PyTorch is not installed! Run setup.ps1 first.")
        sys.exit(1)


def check_pandoc() -> bool:
    """Check if Pandoc is installed."""
    if shutil.which("pandoc"):
        print_success("Pandoc found.")
        return True
    else:
        print_error("Pandoc not found! Install it: winget install JohnMacFarlane.Pandoc")
        return False


def find_pdf_files() -> list[Path]:
    """Find PDF files in the input/ directory."""
    if not INPUT_DIR.exists():
        INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(INPUT_DIR.glob("*.pdf"))


def select_pdf_interactive() -> Path:
    """Prompt the user to select a PDF file."""
    pdf_files = find_pdf_files()

    if not pdf_files:
        print_error(f"No PDF files found in '{INPUT_DIR}'!")
        print_info("Place your PDF file in the following folder and run again:")
        print_info(f"  {INPUT_DIR}")
        sys.exit(1)

    if len(pdf_files) == 1:
        print_success(f"PDF found: {pdf_files[0].name}")
        return pdf_files[0]

    print("\nAvailable PDF files:")
    for i, pdf in enumerate(pdf_files, 1):
        size_mb = pdf.stat().st_size / (1024 * 1024)
        print(f"  \033[96m{i}.\033[0m {pdf.name} ({size_mb:.1f} MB)")

    while True:
        try:
            choice = input(f"\nWhich PDF do you want to convert? (1-{len(pdf_files)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(pdf_files):
                return pdf_files[idx]
        except (ValueError, IndexError):
            pass
        print_warn("Invalid selection, please try again.")


def get_metadata_interactive(pdf_name: str) -> dict:
    """Prompt the user for book metadata."""
    stem = Path(pdf_name).stem

    print("\n\033[96mBook Details\033[0m (leave blank to use defaults):")

    title = input(f"  Title [{stem}]: ").strip() or stem
    author = input("  Author [Unknown]: ").strip() or "Unknown"
    publisher = input("  Publisher []: ").strip() or ""
    lang = input("  Language [en]: ").strip() or "en"

    return {
        "title": title,
        "author": author,
        "publisher": publisher,
        "lang": lang,
    }


# ============================================================
# Conversion steps
# ============================================================
def step_download_models() -> None:
    """Download OCR models (slow on first run, fast afterwards)."""
    from pdf_craft import predownload_models

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print_info("Checking/downloading models...")
    print_info(f"Cache location: {MODELS_DIR}")
    predownload_models(models_cache_path=str(MODELS_DIR))
    print_success("Models ready.")


def step_convert_to_markdown(pdf_path: Path, md_path: Path, images_dir: Path) -> None:
    """Convert PDF to Markdown (main OCR step)."""
    from pdf_craft import transform_markdown

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Estimate page count and time
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        page_count = len(doc)
        doc.close()
        estimated_time = page_count * 27  # ~27 seconds per page
        print_info(f"Total pages: {page_count}")
        print_info(f"Estimated time: ~{estimated_time // 60}min {estimated_time % 60}sec")
    except ImportError:
        print_info("(Page count unavailable — PyMuPDF not installed)")

    print_info("Each page takes ~25-30 seconds.")
    print_info("'torch.Size' and 'attention_mask' warnings during processing are normal.\n")

    start_time = time.time()

    transform_markdown(
        pdf_path=str(pdf_path),
        markdown_path=str(md_path),
        markdown_assets_path=str(images_dir),
        analysing_path=str(TEMP_DIR),
        ocr_size="gundam",  # highest quality model (8GB VRAM is sufficient)
        models_cache_path=str(MODELS_DIR),
        dpi=300,
    )

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print_success(f"Markdown conversion complete! (Time: {minutes}min {seconds}sec)")


def step_fix_hyphenation(md_path: Path) -> None:
    """Fix line-end hyphenation artifacts from PDF scanning.

    PDFs often split words across lines with a hyphen:
      'popu-\\npularity' → 'popularity'
      'bi-\\nlingual'    → 'bilingual'

    This function detects and merges those broken words.
    """
    if not md_path.exists():
        print_warn("Markdown file not found, skipping hyphenation fix.")
        return

    content = md_path.read_text(encoding="utf-8")

    # Fix line-end hyphens:
    # letter + hyphen + newline + lowercase letter → merge words
    # e.g. "popu-\npularity" → "popularity"
    fixed = re.sub(
        r'(\w)-\n(\s*)(\w)',
        lambda m: m.group(1) + m.group(3) if m.group(3).islower() else m.group(0),
        content
    )

    # Fix inline broken hyphens:
    # "popu- larity" → "popularity" (hyphen + space + lowercase)
    fixed = re.sub(
        r'(\w)- (\w)',
        lambda m: m.group(1) + m.group(2) if m.group(2).islower() else m.group(0),
        fixed
    )

    fix_count = content.count('-\n') - fixed.count('-\n')

    md_path.write_text(fixed, encoding="utf-8")
    print_success(f"Hyphenation fixed ({fix_count} corrections applied).")


def step_copy_images(images_dir: Path, media_dir: Path) -> None:
    """Copy extracted images to the media folder."""
    if media_dir.exists():
        shutil.rmtree(media_dir)

    if images_dir.exists() and any(images_dir.iterdir()):
        shutil.copytree(images_dir, media_dir)
        image_count = len(list(media_dir.glob("*")))
        print_success(f"Images copied to media folder ({image_count} files).")
    else:
        media_dir.mkdir(parents=True, exist_ok=True)
        print_warn("No images found (text-only PDF?).")


def step_create_epub(md_path: Path, epub_path: Path, media_dir: Path, metadata: dict) -> None:
    """Build EPUB from Markdown using Pandoc."""
    style_css = SCRIPT_DIR / "style.css"
    style_args = []
    if style_css.exists():
        print_success("style.css found, applying stylesheet.")
        style_args = [f"--css={style_css}"]
    else:
        print_info("style.css not found, generating standard EPUB.")

    cmd = [
        "pandoc",
        str(md_path),
        "-o", str(epub_path),
        "--toc",
        "--toc-depth=3",
        f"--metadata=title:{metadata['title']}",
        f"--metadata=author:{metadata['author']}",
        f"--metadata=lang:{metadata['lang']}",
    ] + style_args

    if metadata.get("publisher"):
        cmd.append(f"--metadata=publisher:{metadata['publisher']}")

    if media_dir.exists():
        cmd.append(f"--extract-media={media_dir}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print_error(f"Pandoc error: {result.stderr}")
        sys.exit(1)

    size_mb = epub_path.stat().st_size / (1024 * 1024)
    print_success(f"EPUB created: {epub_path.name} ({size_mb:.1f} MB)")


def step_cleanup(md_path: Path, images_dir: Path, media_dir: Path) -> None:
    """Optionally remove temporary files."""
    answer = input("\nDelete temporary files (markdown, images)? (y/n) [n]: ").strip().lower()
    if answer == "y":
        if md_path.exists():
            md_path.unlink()
        if images_dir.exists():
            shutil.rmtree(images_dir)
        if media_dir.exists():
            shutil.rmtree(media_dir)
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        print_success("Temporary files deleted.")
    else:
        print_info(f"Markdown file kept: {md_path}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF files to high-quality EPUB format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert.py                                       # interactive mode
  python convert.py input/book.pdf                        # single file
  python convert.py input/book.pdf -o output/book.epub
  python convert.py input/book.pdf --title "Book" --author "Author"
        """,
    )
    parser.add_argument("pdf", nargs="?", help="Path to the PDF file to convert")
    parser.add_argument("-o", "--output", help="Output EPUB file path")
    parser.add_argument("--title", help="Book title")
    parser.add_argument("--author", help="Author name")
    parser.add_argument("--publisher", help="Publisher name")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument(
        "--ocr-size",
        default="gundam",
        choices=["tiny", "small", "base", "large", "gundam"],
        help="OCR model size (default: gundam — highest quality)",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Scan DPI (default: 300)")
    parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup prompt")

    args = parser.parse_args()

    # Header
    print_header("PDF → EPUB Converter")

    # Step 0: System checks
    print_step(0, 6, "Running system checks...")
    check_cuda()
    if not check_pandoc():
        sys.exit(1)

    # Select PDF
    if args.pdf:
        pdf_path = Path(args.pdf).resolve()
        if not pdf_path.exists():
            print_error(f"PDF not found: {pdf_path}")
            sys.exit(1)
    else:
        pdf_path = select_pdf_interactive()

    # Determine metadata
    if args.title:
        metadata = {
            "title": args.title,
            "author": args.author or "Unknown",
            "publisher": args.publisher or "",
            "lang": args.lang,
        }
    else:
        metadata = get_metadata_interactive(pdf_path.name)

    # Determine output paths
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in metadata["title"]).strip()
    epub_filename = f"{safe_title} - {metadata['author']}.epub" if metadata["author"] != "Unknown" else f"{safe_title}.epub"

    if args.output:
        epub_path = Path(args.output).resolve()
    else:
        epub_path = OUTPUT_DIR / epub_filename

    md_path = OUTPUT_DIR / f"{pdf_path.stem}_output.md"
    images_dir = OUTPUT_DIR / f"{pdf_path.stem}_images"
    media_dir = OUTPUT_DIR / f"{pdf_path.stem}_media"

    # Summary
    print(f"\n  PDF       : \033[97m{pdf_path.name}\033[0m ({pdf_path.stat().st_size / (1024*1024):.1f} MB)")
    print(f"  EPUB      : \033[97m{epub_path.name}\033[0m")
    print(f"  Title     : {metadata['title']}")
    print(f"  Author    : {metadata['author']}")
    if metadata.get("publisher"):
        print(f"  Publisher : {metadata['publisher']}")
    print(f"  OCR       : {args.ocr_size} | DPI: {args.dpi}")

    input("\n  Press Enter to start (Ctrl+C to cancel)... ")

    # Step 1: Download models
    print()
    print_step(1, 6, "Checking/downloading OCR models...")
    step_download_models()

    # Step 2: PDF → Markdown
    print()
    print_step(2, 6, "Converting PDF → Markdown...")
    step_convert_to_markdown(pdf_path, md_path, images_dir)

    # Step 3: Fix hyphenation
    print()
    print_step(3, 6, "Fixing hyphenation artifacts...")
    step_fix_hyphenation(md_path)

    # Step 4: Copy images
    print()
    print_step(4, 6, "Organizing images...")
    step_copy_images(images_dir, media_dir)

    # Step 5: Markdown → EPUB
    print()
    print_step(5, 6, "Building EPUB...")
    step_create_epub(md_path, epub_path, media_dir, metadata)

    # Step 6: Cleanup
    print()
    print_step(6, 6, "Cleanup...")
    if not args.no_cleanup:
        step_cleanup(md_path, images_dir, media_dir)
    else:
        print_info("Cleanup skipped (--no-cleanup).")

    # Done
    print_header("Conversion Complete!")
    print(f"  📖 Your EPUB is ready:")
    print(f"  \033[97m{epub_path}\033[0m")
    print()


if __name__ == "__main__":
    main()
