from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_image_contains_gpu_runtime_and_required_tools() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04" in dockerfile
    assert "https://download.pytorch.org/whl/cu126" in dockerfile
    assert "pandoc" in dockerfile
    assert "poppler-utils" in dockerfile
    assert "calibre" in dockerfile
    assert "USER app" in dockerfile
    assert 'ENTRYPOINT ["/usr/bin/tini", "--", "pdf-to-epub-ocr"]' in dockerfile


def test_compose_mounts_user_files_model_cache_and_gpu() -> None:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "./input:/workspace/input" in compose
    assert "./output:/workspace/output" in compose
    assert "models:/cache" in compose
    assert "driver: nvidia" in compose
    assert "capabilities: [gpu]" in compose


def test_docker_context_excludes_local_documents_and_build_artifacts() -> None:
    ignored = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert {".git", "*.pdf", "*.epub", "input", "output", ".test-venv", "dist"} <= ignored
