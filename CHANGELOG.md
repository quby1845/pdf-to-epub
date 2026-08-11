# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

[Unreleased]: https://github.com/quby1845/pdf-to-epub/compare/v0.1.0...HEAD
