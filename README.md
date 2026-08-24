# PDF to EPUB OCR

[![CI](https://github.com/quby1845/pdf-to-epub/actions/workflows/ci.yml/badge.svg)](https://github.com/quby1845/pdf-to-epub/actions/workflows/ci.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/python-3.11--3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Convert scanned PDF books into EPUB, editable Markdown, or legacy MOBI files with local,
GPU-accelerated OCR.
The project combines [pdf-craft](https://github.com/oomol-lab/pdf-craft) for document
recognition, [Pandoc](https://pandoc.org/) for EPUB generation, and
[Calibre](https://calibre-ebook.com/) for optional MOBI packaging. Source documents are processed
on your machine; no document text is sent to an external API.

> [!IMPORTANT]
> This project is in alpha. Keep the original PDF and review generated EPUBs before relying
> on them. OCR output is never guaranteed to be an exact transcription.

**Türkçe kullanım:** [Türkçe kolay kurulum ve kullanım rehberi](README_TR.md)

## Easiest Windows setup (no command line)

1. Download the **Windows easy-start ZIP** from the
   [latest release](https://github.com/quby1845/pdf-to-epub/releases/latest) and extract it.
2. Double-click **`KURULUM.bat`**. It installs the required components and creates desktop and
   Start menu shortcuts. The first setup can take 10–30 minutes because the OCR stack is large.
3. Open **PDF to EPUB OCR** from the desktop or Start menu, select **English** in the header if
   needed, choose a PDF and EPUB, Markdown, or MOBI, confirm the book details, and click
   **Convert**.

The desktop app keeps the document on your computer and saves the selected output beside the
PDF by default. Once setup is complete, the app launches without a command prompt and provides
a normal windowed workflow. NVIDIA CUDA works on Windows 10/11. The AMD ROCm beta path requires
Windows 11, Python 3.12, and one of AMD's officially listed Radeon GPUs.

## Why this project

PDF pages have a fixed layout, while EPUB content adapts to an e-reader's screen and font
settings. PDF to EPUB OCR provides a reproducible command-line workflow for scanned books:

- local DeepSeek OCR through pdf-craft;
- document layout and reading-order detection;
- image preservation and a generated table of contents;
- a complete first-page cover for EPUB and MOBI outputs;
- repair of common line-end hyphenation artifacts;
- conservative cleanup of prose misclassified as mostly empty `None` tables;
- EPUB, editable Markdown, and legacy MOBI outputs;
- configurable language, metadata, OCR model, DPI, and stylesheet;
- a non-interactive CLI suitable for repeatable conversions.

## Requirements

| Component | Supported / recommended |
| --- | --- |
| Operating system | Windows 10/11 for NVIDIA; Windows 11 for AMD ROCm; Linux is community-supported |
| Python | 3.11, 3.12, or 3.13 |
| GPU | Supported NVIDIA CUDA or AMD ROCm GPU; 8 GB is the practical model baseline |
| Memory | 16 GB RAM recommended |
| Disk | At least 20 GB free for Python packages and the 6.5 GB OCR model |
| System tools | Pandoc, Poppler, and Calibre (`ebook-convert`) for MOBI |

Local DeepSeek OCR requires GPU acceleration and does not support CPU conversion. NVIDIA uses
CUDA; supported AMD cards use ROCm. A 6 GB card cannot reliably hold the current unquantized
model. An 8 GB card can work when other GPU applications are closed; more VRAM provides
additional headroom. The OCR quality setting changes page-processing resolution and working
memory, not the 6.5 GB model download or its base weight footprint.

AMD support is currently beta because the upstream OCR packages still describe their local
backend as CUDA-only. PyTorch intentionally exposes AMD ROCm devices through the same
`torch.cuda` API used by those packages, and setup performs a real tensor/kernel probe before
accepting the installation. The official Windows ROCm 7.2.1 list currently covers RX 9070,
RX 9070 XT, AI PRO R9700, RX 9060 XT, RX 7900 XTX, PRO W7900 variants, and RX 7700. AMD requires
Windows 11, Python 3.12, and graphics driver 26.2.2. See AMD's
[Windows compatibility matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/windows/windows_compatibility.html)
and [PyTorch installation guide](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/windows/install-pytorch.html).

## Installation

### Windows quick setup

Clone the repository and run the included PowerShell setup:

```powershell
git clone https://github.com/quby1845/pdf-to-epub.git
cd pdf-to-epub
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

The script detects NVIDIA or a supported AMD Radeon before creating the environment. It installs
CUDA PyTorch for NVIDIA, or AMD's official ROCm 7.2.1/PyTorch 2.9.1 wheels for eligible Windows
11 cards. The managed environment lives at the short, stable
`%LOCALAPPDATA%\PDF-to-EPUB-OCR\venv` path, avoiding Windows path-length failures even when the
downloaded ZIP is deeply nested. It repairs partial environments using real imports and a CUDA
kernel probe, selects CUDA 13 with `sm_120` support for RTX 50 / Blackwell cards, keeps compatible
RTX 30/40 installs, installs the package, and checks Pandoc, Poppler, and Calibre. AMD installs
are pinned to Python 3.12 and are rejected early when the Radeon model is outside AMD's official
Windows support matrix.

### Docker setup (optional CLI workflow)

Docker keeps Python, CUDA libraries, Pandoc, Poppler, Calibre, and the application in one reproducible
container. It runs the command-line interface, not the Windows desktop GUI.

Prerequisites:

- an NVIDIA GPU with a current host driver;
- Docker Desktop with the WSL 2 backend on Windows, or Docker Engine plus NVIDIA Container
  Toolkit on Linux;
- Docker Compose v2 and at least 10 GB of free disk space.

Build the image once:

```bash
git clone https://github.com/quby1845/pdf-to-epub.git
cd pdf-to-epub
docker compose build
```

Put one or more PDFs in `input/`, then start the guided workflow:

```bash
docker compose run --rm converter
```

For a repeatable non-interactive conversion:

```bash
docker compose run --rm converter \
  "input/book.pdf" \
  --output "output/book.epub" \
  --title "Book Title" \
  --author "Author Name" \
  --lang en \
  --ocr-size large \
  --yes
```

The host `input/` and `output/` directories are mounted into the container, while a named Docker
volume keeps downloaded OCR models between runs. Confirm GPU access with:

```bash
docker compose run --rm --entrypoint python converter \
  -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

`docker compose down` stops the project without deleting the model cache. Use
`docker compose down --volumes` only when you intentionally want to remove downloaded models.

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
provides file selection, book metadata, EPUB/Markdown/MOBI output choices, page processing modes,
progress updates, and actionable error messages without requiring a terminal. The interface calls
these choices **page processing modes**: all five use the same 6.5 GB OCR engine, while changing
the page resolution or crop strategy. During OCR it
reports the real current page, total
page count, completion percentage, estimated remaining time after the first three pages, PDF
rendering, and the first model-load/inference phase from pdf-craft's page events. EPUB and MOBI
use the complete first PDF page as a dedicated cover. During page OCR, **Pause** stops work at the
next safe checkpoint without losing completed pages; **Resume** continues the same conversion.
The model remains loaded in VRAM while paused. The complete desktop interface, including dialogs,
progress updates, model guidance, and error messages, can switch instantly between Turkish and
English; the selected language is remembered for the next launch. A persistent light/dark theme
toggle updates the complete interface, including native Windows chrome. The modern step-based
layout uses bundled theme-aware icons, a visual file summary, and clear status feedback; no UI
assets are fetched from the internet.

Advanced users can use the CLI:

```bash
# Installed command
pdf-to-epub-ocr input/book.pdf --title "Book Title" --author "Author Name"

# Editable Markdown (images are saved beside the .md file)
pdf-to-epub-ocr input/book.pdf --format markdown -o output/book.md

# Legacy MOBI for older Kindle workflows (requires Calibre)
pdf-to-epub-ocr input/book.pdf --format mobi -o output/book.mobi

# Equivalent command from a repository checkout
python convert.py input/book.pdf --title "Book Title" --author "Author Name"
```

When an input file is passed, the command is non-interactive. Without an input path it lists
PDF files in `input/` and prompts for book metadata.

Common options:

```text
-o, --output PATH           Explicit .epub, .md, or .mobi output path
--format FORMAT             epub, markdown, or mobi; inferred from -o when omitted
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
--overwrite                 Replace existing output
```

Run `pdf-to-epub-ocr --help` for the complete interface.

## Output and privacy

- EPUB is the default; `--format markdown` and `--format mobi` select the other outputs.
- Markdown images are copied to a sibling `<name>_assets` directory and links are rewritten.
- MOBI is built from an intermediate EPUB with Calibre's `ebook-convert`.
- Intermediate files are removed after a successful conversion by default.
- `--keep-intermediates` preserves the Markdown and extracted assets for inspection.
- Model weights are downloaded by pdf-craft/Hugging Face on first use and reused from the cache;
  the PDF itself remains local. The `snapshots` and `blobs` views can show the same cached weight
  file and should not be manually edited. On Windows the application forces ordinary file copies
  instead of privileged symlinks; optional checkpoint notebook/README artifacts are not required
  for conversion. Review upstream dependency policies if your environment has strict controls.
- The GUI writes a rotating diagnostic log to the per-user application log directory and shows
  its exact path after an error. It records GPU/VRAM, CUDA architecture, model-load, and page-event
  details without recording the PDF text.

## Known limitations

- OCR quality depends on scan resolution, language, typography, and page complexity.
- Complex tables, formulas, marginalia, and right-to-left text may require manual correction.
- Exact PDF pagination and visual layout cannot be preserved in a reflowable EPUB.
- MOBI is a legacy format; EPUB is recommended unless an older device or workflow requires MOBI.
- AMD Windows support is beta and limited to AMD's published ROCm hardware matrix; the automated
  suite cannot execute AMD GPU inference on NVIDIA-hosted CI.
- The automated test suite validates orchestration and text processing without downloading
  models or performing GPU OCR. Maintainers manually validate representative conversion output.

## Troubleshooting

| Symptom | Suggested action |
| --- | --- |
| `PyTorch is not installed` | Install the CUDA build selected for your driver and Python version. |
| `CUDA is not available` | Check the NVIDIA driver and PyTorch CUDA build. CPU runs are not supported. |
| `CUDA/ROCm is not available` | Rerun `KURULUM.bat` so the matching NVIDIA or AMD PyTorch build is installed. |
| Unsupported AMD GPU | Windows AMD beta only accepts models in AMD's ROCm 7.2.1 compatibility matrix. |
| AMD ROCm setup fails | Confirm Windows 11, Python 3.12, Radeon driver 26.2.2, and a supported GPU. |
| `[WinError 206]` during setup | Run the current `KURULUM.bat`; it uses a short managed environment and repairs partial installs. |
| `[WinError 1314]` in the model cache | Upgrade to the current release; it falls back to ordinary copies without admin or Developer Mode. |
| RTX 50 / `no kernel image` | Rerun `KURULUM.bat` so CUDA 13 PyTorch with `sm_120` kernels is selected. |
| `Pandoc was not found` | Install Pandoc, then open a new terminal so `PATH` is refreshed. |
| `Calibre ebook-convert was not found` | Rerun `KURULUM.bat` or install Calibre to enable MOBI output. |
| Poppler/PDF rendering error | Install Poppler and ensure its `bin` directory is on `PATH`. |
| 6 GB VRAM | The full model does not fit reliably; tiny/small only reduce per-page working memory. |
| CUDA out of memory on 8 GB+ | Close GPU-heavy apps, then retry with `--ocr-size base` or `small`. |
| `Failed to extract page 1 layout at stage 1` | Install the latest release and report the detailed CUDA error it now displays, plus GPU model and VRAM. |
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
