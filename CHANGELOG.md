# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Upgrade the Windows AMD backend to AMD's ROCm 7.14 / PyTorch 2.12 packages and require a
  working `torch.distributed.fsdp` import during setup. ROCm 7.2.1 could pass the GPU tensor
  probe but then fail on the first OCR page when Transformers imported the missing C10d module.

## [0.12.1] - 2026-08-25

### Fixed

- Follow AMD's documented Windows ROCm wheel installation sequence without pip's
  `--force-reinstall`, which incorrectly searched PyPI for the ROCm 7.2.1 metapackage and
  aborted after downloading the GPU packages. Include the matching official `torchaudio`
  wheel and remove only existing PyTorch distributions before repair.

## [0.12.0] - 2026-08-24

### Added

- Add the official **PDF to EPUB Receiver** KOReader companion plugin, maintained and released
  from this repository instead of requiring users to install a third-party plugin.
- Add an always-available **Send a file** action so any regular file can be selected and sent to
  KOReader without running a PDF conversion first.
- Build architecture-specific KOReader packages for current ARM devices, ARM64 readers, and
  legacy Kindle hardware.
- Add automatic receiver update support through this project's GitHub releases, deterministic
  plugin packaging, license attribution, and regression tests for the installable ZIP layout.

### Changed

- Point the desktop plugin button and English/Turkish setup instructions to the project's own
  receiver packages while retaining LocalSend v2.2 protocol compatibility.

## [0.11.2] - 2026-08-24

### Fixed

- Split adjacent quoted dialogue into separate paragraphs when OCR joins two speakers, such as
  `?”“`, without rewriting ordinary quotation marks.
- Remove long, near-sequential number-only hallucinations produced by OCR on blank pages while
  preserving short numeric content and real numbered lists.
- Preserve explicit Turkish and English chapter markers (`BÖLÜM`, `Kısım`, `Chapter`, `Part`,
  and `Book`) as Markdown headings so EPUB readers retain visible section boundaries.
- Repair line-wrap hyphenation containing non-breaking spaces and avoid joining words across a
  true blank paragraph boundary.

## [0.11.1] - 2026-08-24

### Fixed

- Do not abort AMD ROCm setup when the Microsoft Visual C++ Runtime is already installed and
  `winget` returns its "no applicable upgrade" result. Setup now verifies the runtime through
  its registry marker and system DLLs before invoking `winget`, then rechecks it after install.
- Treat an installed `winget` package as success even when the install command reports a
  non-zero no-upgrade result, while continuing to fail for genuinely missing packages.

## [0.11.0] - 2026-08-24

### Added

- Add native Linux and macOS setup/repair/check/uninstall scripts, application-menu launchers,
  executable release bundles, and CI smoke tests on both operating systems.
- Add automatic Linux NVIDIA CUDA setup, including the CUDA 13 path for RTX 50 cards, plus an
  official Ubuntu 24.04/Python 3.12 AMD ROCm 7.2.1 installation path and real GPU kernel probe.
- Add platform-specific repair guidance throughout the desktop error flow.
- Add a persistent Turkish/English desktop language switcher covering the full interface,
  file dialogs, model/output labels, progress updates, and actionable error messages.
- Add a real English Windows Setup.exe with per-user installation, Start menu integration,
  Windows uninstall registration, and a modern wizard.
- Add an English Maintenance Center for runtime repair, SHA-256-verified GitHub Release updates,
  and uninstallation while preserving downloaded OCR models by default.
- Add direct **Send to KOReader** support after EPUB/MOBI conversion using the native LocalSend
  v2.2 protocol: same-network device discovery, manual IP fallback, optional PINs, transfer
  progress, mutual-TLS client identity, and receiver certificate fingerprint pinning.

### Changed

- Mark macOS desktop packaging separately from OCR capability: the interface installs and opens,
  but conversion remains disabled until upstream DeepSeek OCR supports Apple Metal/MPS instead
  of requiring CUDA.
- Make English the default desktop language for fresh installations while retaining the
  persistent Turkish switch.
- Keep the easy-start ZIP and batch launchers as legacy troubleshooting tools instead of the
  primary Windows installation path.
- Keep KOReader transfers local to the LAN and reject devices whose HTTPS certificate no longer
  matches the identity announced during discovery.

## [0.9.1] - 2026-08-20

### Added

- Add a cooperative **Pause / Resume** control to the Windows desktop app. OCR waits at its next
  safe checkpoint without discarding completed pages or unloading the model, then continues the
  same conversion.
- Exclude paused time from the live remaining-duration estimate.

## [0.9.0] - 2026-08-20

### Added

- Use the complete first PDF page as the dedicated EPUB/MOBI cover instead of relying on an OCR
  crop.
- Show an estimated remaining duration after three completed pages and continuously refine it as
  conversion progresses.

### Changed

- Rename the desktop selector from OCR quality to page processing mode and explain that every mode
  uses the same 6.5 GB OCR engine while changing page resolution/cropping.

### Fixed

- Conservatively flatten prose that OCR clearly misclassified as a mostly empty table and remove
  literal `None` placeholders, while preserving ordinary data tables.

## [0.8.4] - 2026-08-20

### Fixed

- Prevent the mouse wheel from changing the OCR mode or EPUB/Markdown/MOBI selector while
  scrolling the desktop form; wheel input over either selector now scrolls the page instead.

## [0.8.3] - 2026-08-20

### Fixed

- Keep the Windows installer open after a failure, save the PowerShell error to
  `%LOCALAPPDATA%\PDF-to-EPUB-OCR\logs\install-error.log`, and open that log in Notepad.

## [0.8.2] - 2026-08-20

### Fixed

- Keep the Windows hidden-console `subprocess.Popen` policy as a real class so `asyncio` and
  PyTorch can subclass it without raising `TypeError: function() argument 'code' must be code`.

## [0.8.1] - 2026-08-20

### Fixed

- Run multiline PyTorch GPU validation through a temporary Python file so Windows PowerShell 5.1
  cannot strip quotes and produce a false `SyntaxError` during the easy installation.

## [0.8.0] - 2026-08-20

### Added

- Add beta Windows AMD ROCm 7.2.1 support for AMD's official Radeon compatibility list. The easy
  installer detects NVIDIA versus AMD, requires Windows 11 and Python 3.12 for AMD, installs
  AMD's official PyTorch 2.9.1 ROCm wheels, and verifies the backend with a real GPU tensor.

### Changed

- Make runtime diagnostics backend-aware so ROCm's intentional `torch.cuda` API compatibility
  does not trigger NVIDIA Blackwell checks or misleading CUDA-only errors.

## [0.7.0] - 2026-08-20

### Added

- Add EPUB, editable Markdown, and legacy MOBI output choices to both the desktop application and
  CLI. Markdown exports keep OCR images in a sibling assets directory; MOBI packaging uses
  Calibre's `ebook-convert`.
- Install and validate Calibre in the Windows easy setup and Docker image, with format-specific
  runtime checks and actionable errors.

## [0.6.4] - 2026-08-20

### Changed

- Show each desktop OCR option's processing resolution and clearly labelled approximate total
  VRAM estimate directly in the model selector, with guidance that actual peak usage varies by
  page, crop count, driver, and other GPU applications.

## [0.6.3] - 2026-08-14

### Fixed

- Install the managed Windows virtual environment under the short, stable
  `%LOCALAPPDATA%\PDF-to-EPUB-OCR\venv` path so deeply nested release folders no longer cause
  PyTorch `WinError 206` failures.
- Detect broken or partial virtual environments with real Python and PyTorch imports, then verify
  the completed installation with a CUDA tensor operation instead of checking for a folder.
- Select CUDA 13 PyTorch automatically for RTX 50 / Blackwell GPUs and reject incompatible
  builds that do not contain `sm_120` kernels; keep working RTX 30/40 environments unchanged.
- Force copy-based Hugging Face snapshot materialization for the application cache on Windows,
  avoiding `WinError 1314` without Developer Mode or administrator privileges.
- Hide Poppler, Pandoc, and other helper-process console windows when launched from the GUI.

### Added

- Add total and available VRAM preflight checks, a clear unsupported 6 GB message, an actionable
  low-free-VRAM warning, and an early CUDA kernel compatibility test.
- Distinguish PDF rendering, first model load, and OCR inference in page progress and persistent
  rotating diagnostic logs.
- Add regression coverage for Windows copy-only caching, hidden subprocesses, Blackwell package
  validation, low-VRAM behavior, logging, and installer selection logic.

## [0.6.2] - 2026-08-14

### Fixed

- Stop force-downloading the 6.5 GB DeepSeek OCR model before every conversion attempt; missing
  model files are now downloaded through the cache-aware Transformers loading path.
- Preserve nested pdf-craft and CUDA error details instead of showing only the generic
  `Failed to extract page 1 layout at stage 1` wrapper.
- Stop before downloading OCR weights when CUDA is unavailable and report detected VRAM.

### Changed

- Require pdf-craft 1.0.14 or newer and correct the documented DeepSeek OCR hardware needs.

## [0.6.1] - 2026-08-14

### Fixed

- Skip nonfunctional Microsoft Store/App Execution Alias `python.exe` commands during Windows
  setup instead of aborting before Python can be installed with winget.
- Validate every fallback Python path and cover the broken-alias scenario in Windows CI.

## [0.6.0] - 2026-08-14

### Added

- Add an optional NVIDIA GPU Docker workflow with a CUDA 12.6 runtime, CUDA-enabled PyTorch,
  Pandoc, Poppler, persistent OCR model storage, and host-mounted input/output directories.
- Document guided and non-interactive Docker Compose usage in English and Turkish.
- Validate Docker Compose and Dockerfile syntax in CI and cover the container contract with tests.

## [0.5.0] - 2026-08-13

### Added

- Add a bundled, theme-aware icon set with no network or runtime asset dependency.
- Add a native application icon for the Windows title bar.

### Changed

- Redesign the desktop app with a modern product header, feature summary, visual file picker,
  icon-led step cards, clearer conversion action, and icon-based progress and status feedback.
- Show the selected PDF's filename, size, and folder before conversion.

## [0.4.0] - 2026-08-13

### Added

- Add a persistent light/dark theme toggle to the Windows desktop app.
- Provide complete dark palettes for cards, fields, buttons, status states, progress indicators,
  scrollbars, and the native Windows title bar.

## [0.3.0] - 2026-08-13

### Added

- Display the real current page, total PDF page count, and completion percentage while OCR is
  running in both the desktop app and CLI.
- Switch the desktop progress bar from an activity indicator to measured page progress as soon
  as the OCR engine reports its first page event.

## [0.2.1] - 2026-08-13

### Fixed

- Remove OCR line-wrap hyphens that survive inside Turkish words, including visible Unicode
  hyphens and invisible soft hyphens, while preserving common intentional compounds such as
  `e-posta` and `sosyo-ekonomik`.

## [0.2.0] - 2026-08-13

### Added

- Redesigned Turkish desktop application with a modern card-based interface, clearer model
  guidance, three-stage progress feedback, and one-click result actions.
- Start menu shortcut alongside the desktop shortcut.

### Changed

- Launch installed shortcuts through a hidden window so everyday conversions never show a
  command prompt.
- Improve high-DPI rendering and give validation, privacy, timing, and recovery guidance inside
  the application.

## [0.1.2] - 2026-08-13

### Fixed

- Use ASCII-only Windows batch and PowerShell launchers so legacy `cmd.exe` cannot lose command
  prefixes after multibyte Turkish characters.
- Call Windows PowerShell through its absolute system path and avoid fragile parenthesized error
  branches in the batch installer.
- Execute the actual installer and launcher self-tests under `cmd.exe` and Windows PowerShell in
  CI, and reject non-ASCII launcher scripts during release packaging.

## [0.1.1] - 2026-08-13

### Fixed

- Build Windows easy-start ZIP files with CRLF line endings so `cmd.exe` can run the included
  batch launchers without dropping characters or repeatedly reporting unknown commands.
- Pass the repository explicitly when creating GitHub Releases from a job without a checkout.
- Keep PyPI publishing opt-in until the repository's Trusted Publisher is configured.

## [0.1.0] - 2026-08-13

### Added

- Turkish desktop interface with PDF selection, book metadata, model guidance, progress, and
  friendly error reporting.
- One-click Windows installer/launcher, automatic supported-Python discovery, and a desktop
  shortcut.
- Turkish end-user guide and a downloadable Windows easy-start release bundle.
- Installable `pdf-to-epub-ocr` Python package and console command.
- Unit tests, linting, coverage enforcement, multi-version CI, and package verification.
- Tag-driven GitHub Release and PyPI Trusted Publishing workflow.
- Contribution, security, maintenance, issue, and pull request guidance.
- Configurable model cache, working directory, stylesheet, overwrite behavior, and retained
  intermediate files.

### Changed

- Reworked the README around verifiable capabilities, privacy boundaries, requirements, and
  reproducible setup.
- Made file-based CLI usage non-interactive while retaining the guided `input/` workflow.
- Moved OCR model files to the per-user cache by default.

### Fixed

- Forward `--ocr-size` and `--dpi` values to pdf-craft instead of silently ignoring them.
- Align the documented Python and language defaults with runtime behavior.
- Use Pandoc's resource path correctly when embedding extracted assets.
- Refuse to overwrite an existing EPUB unless explicitly requested.

[Unreleased]: https://github.com/quby1845/pdf-to-epub/compare/v0.9.1...HEAD
[0.9.1]: https://github.com/quby1845/pdf-to-epub/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.8.4...v0.9.0
[0.8.4]: https://github.com/quby1845/pdf-to-epub/compare/v0.8.3...v0.8.4
[0.8.3]: https://github.com/quby1845/pdf-to-epub/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/quby1845/pdf-to-epub/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/quby1845/pdf-to-epub/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.6.4...v0.7.0
[0.6.4]: https://github.com/quby1845/pdf-to-epub/compare/v0.6.3...v0.6.4
[0.6.3]: https://github.com/quby1845/pdf-to-epub/compare/v0.6.2...v0.6.3
[0.6.2]: https://github.com/quby1845/pdf-to-epub/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/quby1845/pdf-to-epub/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/quby1845/pdf-to-epub/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/quby1845/pdf-to-epub/releases/tag/v0.1.0
