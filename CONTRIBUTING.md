# Contributing

Thank you for helping improve PDF to EPUB OCR. Bug reports, documentation fixes, test cases,
and focused pull requests are welcome.

## Before opening an issue

- Search existing issues first.
- Do not attach copyrighted, confidential, or personally identifying PDFs.
- Reduce a failing document to a public or synthetic sample when possible.
- Include the operating system, Python version, GPU model, OCR size, DPI, and complete error
  output.
- Use GitHub's private vulnerability reporting flow for security-sensitive findings; see
  [SECURITY.md](SECURITY.md).

## Development setup

Python 3.11–3.13 is supported.

```bash
python -m venv .venv
# Activate .venv for your shell.
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The unit tests do not download OCR models or require a GPU. A CUDA environment, Poppler, and
Pandoc are required only for an end-to-end conversion.

## Quality checks

Run all checks before opening a pull request:

```bash
ruff check .
ruff format --check .
pytest
python -m build
python -m twine check dist/*
```

New behavior should include tests. Keep changes focused, update the README for user-visible
behavior, and add a concise entry under `Unreleased` in `CHANGELOG.md`.

## Pull requests

1. Fork the repository and create a short-lived branch.
2. Make one coherent change with tests and documentation.
3. Complete the pull request template and describe any manual GPU validation.
4. Respond to review feedback. The maintainer may ask for a smaller patch or an additional
   regression test.

Pull requests require passing CI and maintainer review. Submission does not guarantee inclusion;
the maintainer considers correctness, scope, maintenance cost, compatibility, and licensing.

## Releases

Only maintainers publish releases. The project follows semantic versioning and records changes
in `CHANGELOG.md`. A `vX.Y.Z` tag must match the version in `pyproject.toml`. The release workflow
builds and verifies distributions, creates a GitHub release, and publishes to PyPI through a
trusted publisher after the `pypi` GitHub environment has been configured.
