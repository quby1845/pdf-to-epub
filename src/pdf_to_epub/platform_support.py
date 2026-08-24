"""Platform-specific support labels and repair guidance."""

from __future__ import annotations

import sys
from typing import Literal

DesktopPlatform = Literal["windows", "linux", "macos", "other"]


def desktop_platform(value: str | None = None) -> DesktopPlatform:
    """Normalize Python platform identifiers for user-facing decisions."""
    current = value or sys.platform
    if current == "win32":
        return "windows"
    if current.startswith("linux"):
        return "linux"
    if current == "darwin":
        return "macos"
    return "other"


def repair_action(*, platform: str | None = None, language: str = "en") -> str:
    """Return the installer action appropriate for the active desktop."""
    current = desktop_platform(platform)
    turkish = language.strip().casefold().startswith("tr")
    if current == "windows":
        return (
            "KURULUM.bat dosyasını yeniden çalıştırın."
            if turkish
            else "Open Maintenance Center and select Repair."
        )
    if current in {"linux", "macos"}:
        return (
            "Terminalde ./setup.sh --repair komutunu çalıştırın."
            if turkish
            else "Run ./setup.sh --repair in Terminal."
        )
    return (
        "Kurulum yönergelerini izleyip GPU ortamını onarın."
        if turkish
        else "Follow the installation guide and repair the GPU environment."
    )


def macos_ocr_unavailable(*, language: str = "en") -> str:
    """Explain the upstream CUDA limitation without promising unsupported MPS inference."""
    if language.strip().casefold().startswith("tr"):
        return (
            "Masaüstü uygulaması macOS'ta açılabilir; ancak mevcut DeepSeek OCR motoru CUDA "
            "gerektirdiği için Apple Silicon/Metal (MPS) ile yerel dönüşüm henüz desteklenmiyor."
        )
    return (
        "The desktop app can run on macOS, but the current DeepSeek OCR engine requires CUDA; "
        "local conversion on Apple Silicon/Metal (MPS) is not supported yet."
    )
