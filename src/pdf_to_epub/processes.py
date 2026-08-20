"""Platform-specific child-process behavior."""

from __future__ import annotations

import subprocess
import sys
from typing import Any


def _hidden_windows_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    hidden = dict(kwargs)
    hidden["creationflags"] = int(hidden.get("creationflags", 0)) | int(
        getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    )

    startup_info_type = getattr(subprocess, "STARTUPINFO", None)
    if startup_info_type is not None:
        startup_info = hidden.get("startupinfo") or startup_info_type()
        startup_info.dwFlags |= int(getattr(subprocess, "STARTF_USESHOWWINDOW", 1))
        startup_info.wShowWindow = int(getattr(subprocess, "SW_HIDE", 0))
        hidden["startupinfo"] = startup_info
    return hidden


def install_gui_subprocess_policy(*, platform: str | None = None) -> bool:
    """Hide helper consoles for this GUI process on Windows; remain a no-op elsewhere."""
    if (platform or sys.platform) != "win32":
        return False
    if getattr(subprocess.Popen, "_pdf_to_epub_hidden", False):
        return True

    original = subprocess.Popen

    class HiddenPopen(original):  # type: ignore[misc,valid-type]
        """Popen subclass that keeps the class contract required by asyncio."""

        _pdf_to_epub_hidden = True
        _pdf_to_epub_original = original

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **_hidden_windows_kwargs(kwargs))

    subprocess.Popen = HiddenPopen  # type: ignore[assignment,misc]
    return True
