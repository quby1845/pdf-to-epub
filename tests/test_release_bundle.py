from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from scripts.build_windows_bundle import create_windows_bundle, normalize_batch_line_endings


def test_normalize_batch_line_endings_handles_mixed_input() -> None:
    assert normalize_batch_line_endings(b"one\ntwo\r\nthree\rfour") == (
        b"one\r\ntwo\r\nthree\r\nfour"
    )


def test_windows_bundle_contains_cmd_compatible_launchers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    launcher = repo / "KURULUM.bat"
    launcher.write_bytes(b"@echo off\necho ready\n")
    readme = repo / "README.md"
    readme.write_bytes(b"hello\n")
    output = tmp_path / "easy-start.zip"

    create_windows_bundle(
        repo, output, files=[launcher.relative_to(repo), readme.relative_to(repo)]
    )

    with ZipFile(output) as archive:
        batch_data = archive.read("pdf-to-epub-ocr/KURULUM.bat")
        assert batch_data == b"@echo off\r\necho ready\r\n"
        assert archive.read("pdf-to-epub-ocr/README.md") == b"hello\n"
