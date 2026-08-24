from __future__ import annotations

from pdf_to_epub.platform_support import (
    desktop_platform,
    macos_ocr_unavailable,
    repair_action,
)


def test_desktop_platform_normalizes_python_identifiers() -> None:
    assert desktop_platform("win32") == "windows"
    assert desktop_platform("linux") == "linux"
    assert desktop_platform("linux2") == "linux"
    assert desktop_platform("darwin") == "macos"
    assert desktop_platform("freebsd") == "other"


def test_repair_action_matches_the_installer_for_each_platform() -> None:
    assert "Maintenance Center" in repair_action(platform="win32")
    assert "./setup.sh --repair" in repair_action(platform="linux")
    assert "./setup.sh --repair" in repair_action(platform="darwin")
    assert "KURULUM.bat" in repair_action(platform="win32", language="tr")


def test_macos_limit_is_explicit_in_both_languages() -> None:
    assert "Apple Silicon/Metal (MPS)" in macos_ocr_unavailable()
    assert "henüz desteklenmiyor" in macos_ocr_unavailable(language="tr")
