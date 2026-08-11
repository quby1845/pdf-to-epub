# PDF to EPUB OCR

[![CI](https://github.com/quby1845/pdf-to-epub/actions/workflows/ci.yml/badge.svg)](https://github.com/quby1845/pdf-to-epub/actions/workflows/ci.yml)
[![Python 3.11â€“3.13](https://img.shields.io/badge/python-3.11--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Convert scanned PDF books into reflowable EPUB files with local, GPU-accelerated OCR.
The project combines [pdf-craft](https://github.com/oomol-lab/pdf-craft) for document
recognition with [Pandoc](https://pandoc.org/) for EPUB generation. Source documents are
processed on your machine; no document text is sent to an external API.

> [!IMPORTANT]
> This project is in alpha. Keep the original PDF and review generated EPUBs before relying
> on them. OCR output is never guaranteed to be an exact transcription.

## Why this project

PDF pages have a fixed layout, while EPUB content adapts to an e-reader's screen and font
settings. PDF to EPUB OCR provides a reproducible command-line workflow for scanned books:

- local DeepSeek OCR through pdf-craft;
- document layout and reading-order detection;
- image preservation and a generated table of contents;
- repair of common line-end hyphenation artifacts;
- configurable language, metadata, OCR model, DPI, and stylesheet;
- a non-interactive CLI suitable for repeatable conversions.

## Requirements

| Component | Supported / recommended |
| --- | --- |
| Operating system | Windows 10/11; Linux is community-supported |
| Python | 3.11, 3.12, or 3.13 |
| GPU | NVIDIA CUDA GPU; 8 GB VRAM recommended for `gundam` |
| Memory | 16 GB RAM recommended |
| Disk | At least 10 GB free for Python packages and model files |
| System tools | Pandoc and Poppler |

CPU execution may be technically possible in parts of the dependency stack, but it is not a
supported conversion path and can be impractically slow.

## Installation

### Windows quick setup

Clone the repository and run the included PowerShell setup:

```powershell
git clone https://github.com/quby1845/pdf-to-epub.git
cd pdf-to-epub
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

The script creates `.venv`, installs a CUDA-enabled PyTorch build and the Python package,
checks Pandoc and Poppler, and creates `input/` and `output/` directories.

### Manual setup

Install a CUDA-compatible PyTorch build using the
[official PyTorch selector](https://pytorch.org/get-started/locally/), then install this project:

```bash
python -m venv .venv
# Activate .venv for your shell, then install the project:
python -m pip install --upgrade pip
python -m pip install -e .
```

Install Pandoc and Poppler with your operating system's package manager. The first conversion
downloads OCR models to the user cache unless `--models-dir` is supplied.

The planned PyPI distributioï^<¶‰žËkºwµç`  f"--resource-path={markdown_path.parent}",
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
