"""Platform-specific child-process behavior."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
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

    original: Callable[..., subprocess.Popen[Any]] = subprocess.Popen

    def hidden_popen(*args: Any, **kwargs: Any) -> subprocess.Popen[Any]:
        return original(*args, **_hidden_windows_kwargs(kwargs))

    hidden_popen._pdf_to_epub_hidden = True  # type: ignore[attr-defined]
    hidden_popen._pdf_to_epub_original = original  # type: ignore[attr-defined]
    subprocess.Popen = hidden_popen  # type: ignore[assignment,misc]
    return True
