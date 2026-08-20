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


def test_windows_setup_contains_verified_amd_rocm_path() -> None:
    setup = Path("setup.ps1").read_text(encoding="ascii")
    assert "Test-SupportedAmdGpuName" in setup
    assert "AMD Radeon RX 7900 XTX" in setup
    assert "rocm-rel-7.2.1" in setup
    assert "torch-2.9.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl" in setup
    assert 'if ($gpuProfile.Vendor -eq "amd")' in setup


def test_windows_setup_runs_multiline_torch_probe_from_a_file() -> None:
    setup = Path("setup.ps1").read_text(encoding="ascii")
    assert "function Invoke-PythonCode" in setup
    assert '("p2e-python-" + [guid]::NewGuid() + ".py")' in setup
    assert "& $venvPython -c $torchProbe" not in setup
    assert setup.count("Invoke-PythonCode -Command $venvPython -Code $torchProbe") == 2


def test_windows_installer_keeps_errors_visible_and_writes_a_log() -> None:
    launcher = Path("KURULUM.bat").read_text(encoding="ascii")
    assert "install-error.log" in launcher
    assert '2>"%INSTALL_ERROR_LOG%"' in launcher
    assert 'notepad.exe "%INSTALL_ERROR_LOG%"' in launcher
    assert "PDF_TO_EPUB_INSTALLER_FAILURE_OK" in launcher
    assert 'choice /c K /n /m "Pencereyi kapatmak icin K tusuna basin: "' in launcher
