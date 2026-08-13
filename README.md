# PDF to EPUB OCR

[![CI](https://github.com/quby1845/pdf-to-epub/actions/workflows/ci.yml/badge.svg)](https://github.com/quby1845/pdf-to-epub/actions/workflows/ci.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/python-3.11--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Convert scanned PDF books into reflowable EPUB files with local, GPU-accelerated OCR.
The project combines [pdf-craft](https://github.com/oomol-lab/pdf-craft) for document
recognition with [Pandoc](https://pandoc.org/) for EPUB generation. Source documents are
processed on your machine; no document text is sent to an external API.

> [!IMPORTANT]
> This project is in alpha. Keep the original PDF and review generated EPUBs before relying
> on them. OCR output is never guaranteed to be an exact transcription.

**Türkçe kullanım:** [Türkçe kolay kurulum ve kullanım rehberi](README_TR.md)

## Easiest Windows setup (no command line)

1. Download the **Windows easy-start ZIP** from the
   [latest release](https://github.com/quby1845/pdf-to-epub/releases/latest) and extract it.
2. Double-click **`KURULUM.bat`**. It installs the required components and creates a desktop
   shortcut. The first setup can take 10–30 minutes because the OCR stack is large.
3. Open **PDF to EPUB OCR** from the desktop, select a PDF, confirm the book details, and click
   **EPUB'a Dönüştür**.

The desktop app keeps the document on your computer and saves the EPUB beside the selected PDF
by default. A supported conversion currently requires Windows 10/11 and an NVIDIA CUDA GPU.

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

The planned PyPI distribution name is `pdf-to-epub-ocr`; it was available when the release
metadata was prepared. Installation from PyPI will be documented after the first release.

## Usage

For most Windows users, open the desktop shortcut created by `KURULUM.bat`. The graphical app
provides file selection, book metadata, OCR quality choices, progress updates, and actionable
error messages without requiring a terminal.

Advanced users can use the CLI:

```bash
# Installed command
pdf-to-epub-ocr input/book.pdf --title "Book Title" --author "Author Name"

# Equivalent command from a repository checkout
python convert.py input/book.pdf --title "Book Title" --author "Author Name"
```

When an input file is passed, the command is non-interactive. Without an input path it lists
PDF files in `input/` and prompts for book metadata.

Common options:

```text
-o, --output PATH           Explicit EPUB output path
--title TEXT                Book title (defaults to the PDF filename)
--author TEXT               Author (defaults to Unknown)
--publisher TEXT            Publisher metadata
--lang TAG                  EPUB language tag (defaults to en)
--ocr-size SIZE             tiny, small, base, large, or gundam
--dpi NUMBER                Render DPI, from 72 to 600 (defaults to 300)
--css PATH                  Custom EPUB stylesheet
--no-css                    Do not embed a stylesheet
--models-dir PATH           OCR model cache directory
--work-dir PATH             Parent directory for intermediate files
--keep-intermediates        Retain Markdown and extracted assets
--overwrite                 Replace an existing EPUB
```

Run `pdf-to-epub-ocr --help` for the complete interface.

## Output and privacy

- The final EPUB is written to `output/` unless `-o` is used.
- Intermediate files are removed after a successful conversion by default.
- `--keep-intermediates` preserves the Markdown and extracted assets for inspection.
- Model weights are downloaded by pdf-craft/Hugging Face on first use; the PDF itself remains
  local. Review upstream dependency policies if your environment has strict network controls.

## Known limitations

- OCR quality depends on scan resolution, language, typography, and page complexity.
- Complex tables, formulas, marginalia, and right-to-left text may require manual correction.
- Exact PDF pagination and visual layout cannot be preserved in a reflowable EPUB.
- The automated test suite validates orchestration and text processing without downloading
  models or performing GPU OCR. Maintainers manually validate representative conversion output.

## Troubleshooting

| Symptom | Suggested action |
| --- | --- |
| `PyTorch is not installed` | Install the CUDA build selected for your driver and Python version. |
| `CUDA is not available` | Check the NVIDIA driver and PyTorch CUDA build. CPU runs are not supported. |
| `Pandoc was not found` | Install Pandoc, then open a new terminal so `PATH` is refreshed. |
| Poppler/PDF rendering error | Install Poppler and ensure its `bin` directory is on `PATH`. |
| CUDA out of memory | Retry with `--ocr-size large` or `--ocr-size base` and close GPU-heavy apps. |
| Existing output error | Choose another `-o` path or pass `--overwrite`. |

When reporting a bug, do not upload copyrighted or confidential PDFs. Provide a minimal public
sample or a description of the document characteristics whenever possible.

## Development and maintenance

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
python -m build
python -m twine check dist/*
```

The project uses semantic versioning, a Keep a Changelog-style changelog, automated tests on
Python 3.11–3.13, and a tag-driven release workflow with PyPI Trusted Publishing preparation.
See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md),
[CHANGELOG.md](CHANGELOG.md), and [MAINTAINERS.md](MAINTAINERS.md).

## Credits

- [pdf-craft](https://github.com/oomol-lab/pdf-craft) — OCR and document transformation
- [DeepSeek OCR](https://github.com/deepseek-ai/DeepSeek-OCR) — document recognition model
- [Pandoc](https://pandoc.org/) — EPUB generation
- [Poppler](https://poppler.freedesktop.org/) — PDF rendering dependency

## License

Licensed under the [MIT License](LICENSE). Third-party dependencies retain their own licenses.
