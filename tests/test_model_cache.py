from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from pdf_to_epub.model_cache import _is_within, configure_huggingface_cache


def test_path_containment_is_boundary_safe(tmp_path: Path) -> None:
    root = tmp_path / "models"
    assert _is_within(root / "repos" / "one", root)
    assert not _is_within(tmp_path / "models-other", root)


def test_windows_model_cache_forces_copy_without_admin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[object] = []

    def original(cache_dir: object = None) -> bool:
        calls.append(cache_dir)
        return True

    file_download = types.SimpleNamespace(are_symlinks_supported=original)
    package = types.ModuleType("huggingface_hub")
    package.file_download = file_download  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "huggingface_hub", package)

    models = tmp_path / "models"
    assert configure_huggingface_cache(models, os_name="nt")
    assert file_download.are_symlinks_supported(models / "models--deepseek-ai") is False
    assert file_download.are_symlinks_supported(tmp_path / "unrelated") is True
    assert calls == [tmp_path / "unrelated"]


def test_non_windows_model_cache_keeps_upstream_behavior(tmp_path: Path) -> None:
    assert configure_huggingface_cache(tmp_path / "models", os_name="posix") is False
