from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.build_unix_bundle import create_unix_bundle
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
    "filename",
    [
        "KURULUM.bat",
        "PDF-TO-EPUB.bat",
        "start.bat",
        "setup.ps1",
        "launch.ps1",
        "installer/maintenance.ps1",
        "installer/uninstall-cleanup.ps1",
    ],
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
    assert "torchaudio-2.9.1%2Brocm7.2.1-cp312-cp312-win_amd64.whl" in setup
    assert 'if ($gpuProfile.Vendor -eq "amd")' in setup


def test_windows_amd_install_does_not_force_reinstall_rocm_dependencies() -> None:
    setup = Path("setup.ps1").read_text(encoding="ascii")
    amd_function = setup.split("function Install-AmdRocmPyTorch", 1)[1].split(
        "if ($PythonProbeSelfTest)", 1
    )[0]

    assert "pip uninstall --yes torch torchvision torchaudio" in amd_function
    assert "pip install --no-cache-dir @torchPackages" in amd_function
    assert "--force-reinstall @torchPackages" not in amd_function


def test_windows_setup_accepts_an_existing_visual_cpp_runtime() -> None:
    setup = Path("setup.ps1").read_text(encoding="ascii")
    assert "function Test-VisualCppRuntime" in setup
    assert "VC\\Runtimes\\x64" in setup
    assert "vcruntime140.dll" in setup
    assert "msvcp140.dll" in setup
    assert "function Test-WingetPackageInstalled" in setup
    assert "winget reported no applicable upgrade" in setup
    assert "if (Test-VisualCppRuntime)" in setup


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
    assert 'choice /c C /n /m "Press C to close this window: "' in launcher


def test_real_windows_installer_has_stable_upgrade_and_maintenance_integration() -> None:
    installer = Path("installer/pdf-to-epub.iss").read_text(encoding="utf-8")
    assert "AppId={#AppIdValue}" in installer
    assert "PrivilegesRequired=lowest" in installer
    assert "WizardStyle=modern" in installer
    assert "SetupLogging=yes" in installer
    assert "AppModifyPath=" in installer
    assert "maintenance.ps1" in installer
    assert "uninstall-cleanup.ps1" in installer
    assert "-Operation Install -SkipShortcuts -LogPath" in installer
    assert "ResultCode <> 0" in installer
    assert "windows-setup" in installer


def test_maintenance_updates_require_sha256_verification() -> None:
    maintenance = Path("installer/maintenance.ps1").read_text(encoding="ascii")
    assert "Repair" in maintenance
    assert "Check for updates" in maintenance
    assert "Uninstall" in maintenance
    assert "Get-FileHash" in maintenance
    assert "SHA256" in maintenance
    assert "browser_download_url" in maintenance
    assert "Update verification failed" in maintenance


def test_release_workflow_builds_and_publishes_setup_exe() -> None:
    workflow = Path(".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "windows-installer:" in workflow
    assert "Inno Setup 6\\ISCC.exe" in workflow
    assert "windows-setup.exe.sha256" in workflow
    assert "unix-bundles:" in workflow
    assert "build_unix_bundle.py --platform linux" in workflow
    assert "build_unix_bundle.py --platform macos" in workflow
    assert (
        "needs: [build, windows-bundle, windows-installer, unix-bundles, koreader-plugin]"
        in workflow
    )
    assert "koreader-plugin:" in workflow
    assert "pdf-to-epub-receiver-koplugin-${arch}.zip" in workflow
    assert "gh release view" in workflow
    assert "gh release upload" in workflow
    assert "--clobber" in workflow


def test_unix_bundle_preserves_executable_installers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src" / "pdf_to_epub").mkdir(parents=True)
    for name in ("setup.sh", "launch.sh"):
        (repo / name).write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    for name in ("pyproject.toml", "README.md", "README_TR.md", "CHANGELOG.md", "LICENSE"):
        (repo / name).write_text(name, encoding="utf-8")
    (repo / "src" / "pdf_to_epub" / "__init__.py").write_text("", encoding="utf-8")

    output = tmp_path / "linux.zip"
    create_unix_bundle(repo, output, platform="linux")
    with ZipFile(output) as archive:
        setup = archive.getinfo("pdf-to-epub-ocr-linux/setup.sh")
        assert (setup.external_attr >> 16) & 0o111
        assert archive.read("pdf-to-epub-ocr-linux/README.md") == b"README.md"


def test_unix_setup_has_platform_backends_and_safe_operations() -> None:
    setup = Path("setup.sh").read_text(encoding="utf-8")
    assert "PDF_TO_EPUB_UNIX_SETUP_OK" in setup
    assert 'BACKEND="auto"' in setup
    assert "rocm-rel-7.2.1" in setup
    assert "cu130" in setup and "cu126" in setup
    assert "torch.cuda.is_available" in setup
    assert "Apple Silicon/Metal (MPS)" in setup
    assert "--uninstall" in setup and "--repair" in setup and "--check" in setup
