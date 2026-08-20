"""Hugging Face cache compatibility helpers."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def configure_huggingface_cache(models_dir: Path, *, os_name: str | None = None) -> bool:
    """Force copy-based cache materialization on Windows.

    Hugging Face normally prefers snapshot symlinks. Ordinary Windows accounts may receive
    WinError 1314 when symlink creation is not permitted. pdf-craft imports Transformers lazily,
    so installing this policy before importing pdf-craft also covers its transitive downloads.
    """
    if (os_name or os.name) != "nt":
        return False

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from huggingface_hub import file_download

    roots: set[Path] = getattr(file_download, "_pdf_to_epub_copy_roots", set())
    roots.add(models_dir.resolve())
    file_download._pdf_to_epub_copy_roots = roots

    if getattr(file_download.are_symlinks_supported, "_pdf_to_epub_wrapper", False):
        return True

    original: Callable[[str | Path | None], bool] = file_download.are_symlinks_supported

    def copies_for_app_cache(cache_dir: str | Path | None = None) -> bool:
        candidate = Path(cache_dir or models_dir)
        configured_roots: set[Path] = getattr(file_download, "_pdf_to_epub_copy_roots", set())
        if any(_is_within(candidate, root) for root in configured_roots):
            return False
        return original(cache_dir)

    copies_for_app_cache._pdf_to_epub_wrapper = True  # type: ignore[attr-defined]
    file_download.are_symlinks_supported = copies_for_app_cache
    return True
