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

## Desktop setup

### Windows (recommended, no command line)

1. Download the **`windows-setup.exe`** file from the
   [latest release](https://github.com/quby1845/pdf-to-epub/releases/latest).
2. Open Setup and follow the English installation wizard. It installs the required GPU runtime
   and creates desktop and Start menu shortcuts. The first setup can take 10–30 minutes because
   the OCR stack is large.
3. Open **PDF to EPUB OCR**, choose a PDF and EPUB, Markdown, or MOBI, confirm the book details,
   and click **Convert**.

The desktop app keeps the document on your computer and saves the selected output beside the
PDF by default. The Windows **Maintenance Center** provides Repair, verified Check for Updates,
and Uninstall controls. Updates are downloaded from GitHub Releases and must pass the published
SHA-256 check before Setup can launch. Once setup is complete, the app launches without a command
prompt and provides a normal windowed workflow. NVIDIA CUDA works on Windows 10/11. The AMD ROCm
beta path requires Windows 11, Python 3.12, and one of AMD's officially listed Radeon GPUs.

The legacy easy-start ZIP and `KURULUM.bat` remain available as a troubleshooting fallback, but
new users should use Setup.exe.

### Linux

Download the `linux.zip` asset from the latest release, extract it, then run:

```bash
chmod +x setup.sh launch.sh
./setup.sh
```

The installer uses a private environment under `~/.local/share/pdf-to-epub-ocr`, installs a
launcher in `~/.local/bin`, and adds **PDF to EPUB OCR** to the desktop application menu. It can
detect an NVIDIA GPU and choose CUDA 12.6 or CUDA 13 for RTX 50 cards. On supported AMD systems,
the automated ROCm path uses AMD's official ROCm 7.2.1 wheels and currently requires x86-64
Ubuntu 24.04 with Python 3.12 and a correctly installed Radeon/ROCm driver.

Useful maintenance commands:

```bash
./setup.sh --check
./setup.sh --repair
./setup.sh --uninstall
```

### macOS

Download the `macos.zip` asset, extract it, and run the same `chmod` and `./setup.sh` commands.
Setup installs the GUI as `~/Applications/PDF to EPUB OCR.app` and uses Homebrew for Python, Tk,
Pandoc, Poppler, and optional Calibre support.

> [!WARNING]
> The desktop interface installs and opens on macOS, but local OCR conversion is not available
> on Apple Silicon/Metal yet. The upstream pdf-craft/DeepSeek OCR stack currently requires a CUDA
> environment; its CPU package is intended for development and Apple MPS is not supported. The
> app reports this limitation directly instead of starting a conversion that cannot finish.

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
- one-click delivery of any file to KOReader with the project's own receiver plugin;
- configurable language, metadata, OCR model, DPI, and stylesheet;
- a non-interactive CLI suitable for repeatable conversions.

## Requirements

| Component | Supported / recommended |
| --- | --- |
| Operating system | Windows 10/11; Linux (NVIDIA, or supported AMD ROCm); macOS GUI only until upstream MPS support |
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
`torch.cuda` API used by those packages. Windows setup installs AMD's ROCm 7.14 / PyTorch 2.12
multi-architecture packages and verifies both a real GPU tensor and the distributed/FSDP import
used by Transformers before accepting the installation. AMD requires Windows 11, Python 3.12,
a supported Radeon GPU, and a driver compatible with ROCm 7.14. See AMD's
[ROCm 7.14 compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html)
and [PyTorch installation guide](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html).

Linux AMD support uses AMD's published Radeon ROCm 7.2.1 wheels on the supported Ubuntu/Python
combination. Check AMD's
[Linux compatibility matrix](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html)
before installation. Other Linux distributions can use NVIDIA CUDA through `setup.sh`; manual
ROCm setups remain possible but are not claimed as automatically supported.

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
CUDA PyTorch for NVIDIA, or AMD's official ROCm 7.14/PyTorch 2.12 packages for eligible Windows
11 cards. The managed environment lives at the short, stable
`%LOCALAPPDATA%\PDF-to-EPUB-OCR\venv` path, avoiding Windows path-length failures even when the
downloaded ZIP is deeply nested. It repairs partial environments using real imports and a CUDA
kernel probe, selects CUDA 13 with `sm_120` support for RTX 50 / Blackwell cards, keeps compatible
RTX 30/40 installs, installs the package, and checks Pandoc, Poppler, and Calibre. AMD installs
are pinned to Python 3.12 and are rejected early when the Radeon model is outside AMD's official
Windows support matrix.

### Linux and macOS setup script

When installing from a repository checkout instead of a release ZIP:

```bash
git clone https://github.com/quby1845/pdf-to-epub.git
cd pdf-to-epub
chmod +x setup.sh launch.sh
./setup.sh
```

Use `./launch.sh` if your desktop menu has not refreshed. `setup.sh` detects broken managed
environments using real Python imports and validates Linux GPU installations with an actual
tensor/kernel operation. `--skip-system-packages` is available when Pandoc, Poppler, Tk, and
Calibre are already managed by the operating system administrator.

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

Open the desktop shortcut created by Setup.exe on Windows, the application-menu entry on Linux,
or the app under `~/Applications` on macOS. The graphical app
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
progress updates, model guidance, and error messages, can switch instantly between English and
Turkish. Fresh installations start in English and the selected language is remembered for later
launches. A persistent light/dark theme
toggle updates the complete interface, including native Windows chrome. The modern step-based
layout uses bundled theme-aware icons, a visual file summary, and clear status feedback; no UI
assets are fetched from the internet.

### Send any file directly to KOReader

Select **Send a file** at any time to choose an existing file without running a conversion. A
finished conversion can also be sent with **Send to KOReader** in the result bar. The app and its
official **PDF to EPUB Receiver** plugin use the open LocalSend v2.2 LAN protocol; data travels
directly from the computer to the e-reader and is not uploaded to a cloud relay.

#### 1. Choose the receiver package

Download the matching ZIP from the
[latest release](https://github.com/quby1845/pdf-to-epub/releases/latest):

| Package | Typical devices |
| --- | --- |
| `pdf-to-epub-receiver-koplugin-armv7.zip` | Current Kindle, Kobo, PocketBook, and reMarkable 2 devices |
| `pdf-to-epub-receiver-koplugin-arm64.zip` | reMarkable Paper Pro and other ARM64 KOReader devices |
| `pdf-to-epub-receiver-koplugin-arm-legacy.zip` | Kindle 3/DX and older ARM devices |

#### 2. Install it in KOReader

1. Close KOReader and connect the reader to the computer.
2. Open KOReader's `plugins` directory. Common locations are
   `koreader/plugins` on Kindle and `.adds/koreader/plugins` on Kobo. Create the `plugins`
   directory if it does not exist.
3. Extract the ZIP there. The final layout must contain
   `plugins/pdf_to_epub_receiver.koplugin/main.lua`; avoid an extra nested ZIP folder.
4. Safely eject the reader and restart KOReader completely.

#### 3. Recommended first-time settings

Open **Menu → Network → PDF to EPUB Receiver**. Configure these while the server is stopped:

- **Save directory:** choose where received files should be stored.
- **Settings → Allowed extensions (all):** keep this selected to receive any file type.
- **Settings → Use HTTPS:** keep enabled for encrypted local transfers.
- **Settings → PIN code:** optional, but recommended on shared Wi-Fi networks. Enter the same PIN
  in the desktop send window.
- **Settings → Start with KOReader:** optional; enables the receiver automatically after KOReader
  starts and Wi-Fi is available.
- **Settings → File type routing:** optional; can route EPUB, PDF, or other extensions into
  different folders.

Return to the receiver menu and select **Start server**. The menu text changes to
**PDF to EPUB Receiver (running)** when it is ready.

#### 4. Send a file

Keep the e-reader and computer on the same Wi-Fi network. In PDF to EPUB OCR, select
**Send a file** to choose any existing file, or use **Send to KOReader** after a conversion.
Choose the discovered reader, enter its PIN when configured, select **Send file**, and approve
the request shown by KOReader.

If multicast discovery is blocked by a guest network, VPN, or router setting, enter the
e-reader's IP address manually (for example `192.168.1.50`). Every regular file type is supported
by default; KOReader's receiver settings can optionally restrict allowed extensions. HTTPS
transfers use a persistent local client certificate and pin the receiver's announced certificate
fingerprint before sending data.

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
- macOS packaging and GUI launch are tested, but actual local OCR is blocked because the upstream
  DeepSeek OCR engine currently requires CUDA and does not support Apple Metal/MPS.
- Automated Linux AMD setup is intentionally limited to the official Ubuntu 24.04, Python 3.12,
  x86-64 ROCm 7.2.1 wheel combination; unsupported distributions are not modified automatically.
- The automated test suite validates orchestration and text processing without downloading
  models or performing GPU OCR. Maintainers manually validate representative conversion output.

## Troubleshooting

| Symptom | Suggested action |
| --- | --- |
| `PyTorch is not installed` | Install the CUDA build selected for your driver and Python version. |
| `CUDA is not available` | Check the NVIDIA driver and PyTorch CUDA build. CPU runs are not supported. |
| `CUDA/ROCm is not available` | Open Maintenance Center and select **Repair** so the matching NVIDIA or AMD PyTorch build is installed. |
| Unsupported AMD GPU | Windows AMD beta only accepts models in AMD's ROCm 7.14 compatibility matrix. |
| AMD ROCm setup fails | Confirm Windows 11, Python 3.12, a ROCm 7.14-compatible Radeon driver, and a supported GPU. |
| AMD conversion stops on page 1 with `_distributed_c10d` | Install the latest release and run **Repair** to replace the legacy ROCm 7.2.1 stack with ROCm 7.14/PyTorch 2.12. |
| `[WinError 206]` during setup | Open Maintenance Center and select **Repair**; it uses a short managed environment and replaces partial installs. |
| `[WinError 1314]` in the model cache | Upgrade to the current release; it falls back to ordinary copies without admin or Developer Mode. |
| RTX 50 / `no kernel image` | Open Maintenance Center and select **Repair** so CUDA 13 PyTorch with `sm_120` kernels is selected. |
| `Pandoc was not found` | Install Pandoc, then open a new terminal so `PATH` is refreshed. |
| `Calibre ebook-convert was not found` | Select **Repair** in Maintenance Center or install Calibre to enable MOBI output. |
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
