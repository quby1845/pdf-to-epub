from __future__ import annotations

import subprocess

import pytest

from pdf_to_epub.processes import _hidden_windows_kwargs, install_gui_subprocess_policy


def test_hidden_windows_kwargs_preserve_and_add_creation_flags() -> None:
    kwargs = _hidden_windows_kwargs({"creationflags": 4, "cwd": "work"})
    assert kwargs["creationflags"] & 0x08000000
    assert kwargs["creationflags"] & 4
    assert kwargs["cwd"] == "work"


def test_gui_policy_is_noop_outside_windows() -> None:
    assert install_gui_subprocess_policy(platform="linux") is False


def test_gui_policy_hides_all_subprocesses_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    class OriginalPopen:
        def __init__(self, *_args: object, **kwargs: object) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(subprocess, "Popen", OriginalPopen)

    assert install_gui_subprocess_policy(platform="win32") is True
    process = subprocess.Popen(["pdftoppm"], cwd="work")
    assert isinstance(process, OriginalPopen)
    assert isinstance(subprocess.Popen, type)

    class AsyncioCompatiblePopen(subprocess.Popen):
        pass

    assert issubclass(AsyncioCompatiblePopen, OriginalPopen)
    passed_kwargs = calls[-1]
    assert passed_kwargs["creationflags"] & 0x08000000
    assert passed_kwargs["cwd"] == "work"
