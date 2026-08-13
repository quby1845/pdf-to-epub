# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/quby1845/pdf-to-epub/releases/tag/v0.1.0
