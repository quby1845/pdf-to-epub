from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.build_windows_bundle import (
    create_windows_bundle,
    normalize_batch_line_endings,
    require_ascii_windows_script,
)


def test_normalize_batch_line_endings_handles_mixed_input() -> None:
    assert normalize_batch_line_endings(b"one\ntwo\r\nthree\rfour") == (
        b"one\r\ntwo\r\nthree\r\nfour"
    )


@pytest.mark.parametrize("filename", ["KURULUM.bat", "setup.ps1"])
def test_windows_scripts_reject_non_ascii_text(filename: str) -> None:
    with pytest.raises(ValueError, match="ASCII only"):
        require_ascii_windows_script("Türkçe".encode(), Path(filename))


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


@pytest.mark.parametrize(
    "filename", ["KURULUM.bat", "PDF-TO-EPUB.bat", "start.bat", "setup.ps1", "launch.ps1"]
)
def test_repository_windows_launchers_are_ascii(filename: str) -> None:
    Path(filename).read_bytes().decode("ascii")


def test_windows_setup_installs_calibre_for_mobi_output() -> None:
    setup = Path("setup.ps1").read_text(encoding="ascii")
    assert 'Install-WingetPackage -Id "calibre.calibre"' in setup
    assert "ebook-convert.exe" in setup
