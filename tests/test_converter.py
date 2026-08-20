from __future__ import annotations

import sys
import threading
import types
from pathlib import Path
from unittest.mock import Mock

import pytest

from pdf_to_epub.converter import (
    BookMetadata,
    ConversionError,
    ConversionOptions,
    ConversionPauseController,
    ConversionProgress,
    _pandoc_command,
    accelerator_backend,
    check_runtime,
    cleanup_ocr_tables,
    convert_pdf,
    create_epub,
    create_mobi,
    estimate_remaining_seconds,
    export_markdown,
    fix_hyphenation,
    fix_hyphenation_file,
    markdown_assets_output_path,
    output_format_from_path,
    sanitize_filename,
    suggested_output_name,
    validate_options,
)


class FakeCudaTensor:
    def add_(self, _value: int) -> FakeCudaTensor:
        return self


def fake_torch(
    *,
    total_gib: float,
    free_gib: float,
    capability: tuple[int, int] = (8, 9),
    architectures: list[str] | None = None,
    backend: str = "cuda",
) -> types.SimpleNamespace:
    fake_cuda = types.SimpleNamespace(
        is_available=lambda: True,
        get_device_properties=lambda _device: types.SimpleNamespace(
            total_memory=total_gib * 1024**3,
            name="Test NVIDIA GPU",
        ),
        get_device_capability=lambda _device: capability,
        mem_get_info=lambda _device: (free_gib * 1024**3, total_gib * 1024**3),
        get_arch_list=lambda: architectures or [f"sm_{capability[0]}{capability[1]}"],
        synchronize=lambda: None,
    )
    return types.SimpleNamespace(
        __version__="test",
        version=types.SimpleNamespace(
            cuda="test" if backend == "cuda" else None,
            hip="test" if backend == "rocm" else None,
        ),
        cuda=fake_cuda,
        ones=lambda *_args, **_kwargs: FakeCudaTensor(),
    )


def options(tmp_path: Path, **overrides: object) -> ConversionOptions:
    pdf_path = tmp_path / "source.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    values = {
        "pdf_path": pdf_path,
        "epub_path": tmp_path / "result.epub",
        "metadata": BookMetadata("A Book", "An Author", "Press", "tr"),
        "models_dir": tmp_path / "models",
        "work_parent": tmp_path / "work",
        "css_path": None,
    }
    values.update(overrides)
    return ConversionOptions(**values)


def test_filename_helpers_preserve_unicode_and_handle_empty_values() -> None:
    assert sanitize_filename("  Çağrı: Bir / Kitap.  ") == "Çağrı Bir  Kitap"
    assert sanitize_filename("...", fallback="fallback") == "fallback"
    assert suggested_output_name(BookMetadata("Kitap", "Yazar")) == "Kitap - Yazar.epub"
    assert suggested_output_name(BookMetadata("Kitap")) == "Kitap.epub"
    assert suggested_output_name(BookMetadata("Kitap"), "markdown") == "Kitap.md"
    assert suggested_output_name(BookMetadata("Kitap"), "mobi") == "Kitap.mobi"
    assert output_format_from_path(Path("BOOK.MD")) == "markdown"
    with pytest.raises(ConversionError, match="extensions"):
        output_format_from_path(Path("book.txt"))


def test_fix_hyphenation_only_merges_lowercase_continuations(tmp_path: Path) -> None:
    text = "popu-\nlar and bi- lingual but ISO-\nStandard"
    fixed, count = fix_hyphenation(text)
    assert fixed == "popular and bilingual but ISO-\nStandard"
    assert count == 2

    markdown = tmp_path / "book.md"
    markdown.write_text("hel-\nlo", encoding="utf-8")
    assert fix_hyphenation_file(markdown) == 1
    assert markdown.read_text(encoding="utf-8") == "hello"


def test_fix_hyphenation_repairs_turkish_ocr_hyphens_without_breaking_compounds() -> None:
    text = (
        "olup bit-miş bir şeyleri, çalış‐mıştı ve kitap‑ların arasında; "
        "e-posta, sosyo-ekonomik, yavaş-yavaş ve Türk-Alman ilişkileri"
    )
    fixed, count = fix_hyphenation(text, language="tr")

    assert fixed == (
        "olup bitmiş bir şeyleri, çalışmıştı ve kitapların arasında; "
        "e-posta, sosyo-ekonomik, yavaş-yavaş ve Türk-Alman ilişkileri"
    )
    assert count == 3


def test_fix_hyphenation_handles_soft_and_unicode_line_break_hyphens() -> None:
    fixed, count = fix_hyphenation("gösteri\u00adlen ve popü‐\nler ama ISO‑\nStandard", "tr")
    assert fixed == "gösterilen ve popüler ama ISO‑\nStandard"
    assert count == 2


def test_fix_hyphenation_file_requires_generated_markdown(tmp_path: Path) -> None:
    with pytest.raises(ConversionError, match="Markdown was not found"):
        fix_hyphenation_file(tmp_path / "missing.md")


def test_cleanup_ocr_tables_flattens_only_obvious_prose_misclassification() -> None:
    text = (
        "Before\n\n"
        "| None | This is a normal paragraph with enough words to be prose, not tabular data. |\n"
        "| --- | --- |\n"
        "| None | None |\n\n"
        "| Name | Value |\n"
        "| --- | --- |\n"
        "| Alice | None |\n"
    )
    fixed, count = cleanup_ocr_tables(text)

    assert "This is a normal paragraph" in fixed
    assert "| None | This is" not in fixed
    assert "| Name | Value |" in fixed
    assert "| Alice | None |" in fixed
    assert count == 1


def test_cleanup_ocr_tables_handles_html_and_preserves_real_tables() -> None:
    broken = (
        "<table><tr><td>None</td><td>A long paragraph that was incorrectly placed inside "
        "a table by the OCR layout detector.</td></tr><tr><td>None</td><td>None</td></tr></table>"
    )
    real = "<table><tr><th>Name</th><th>Value</th></tr><tr><td>A</td><td>1</td></tr></table>"
    fixed, count = cleanup_ocr_tables(f"{broken}\n\n{real}")

    assert "<table>" not in fixed.split("\n\n", maxsplit=1)[0]
    assert "incorrectly placed" in fixed
    assert real in fixed
    assert count == 1


def test_remaining_time_estimate_waits_for_three_pages() -> None:
    assert estimate_remaining_seconds(elapsed_seconds=60, completed_pages=2, total_pages=10) is None
    assert estimate_remaining_seconds(elapsed_seconds=90, completed_pages=3, total_pages=12) == 270
    assert (
        estimate_remaining_seconds(elapsed_seconds=90, completed_pages=12, total_pages=12) is None
    )


def test_pause_controller_blocks_worker_until_resume() -> None:
    controller = ConversionPauseController()
    finished = threading.Event()

    assert controller.pause() is True
    assert controller.pause() is False
    assert controller.is_paused is True

    worker = threading.Thread(
        target=lambda: (controller.wait_if_paused(), finished.set()),
        daemon=True,
    )
    worker.start()
    assert finished.wait(0.05) is False

    assert controller.resume() is True
    assert controller.resume() is False
    assert finished.wait(1) is True
    worker.join(timeout=1)
    assert controller.is_paused is False
    assert controller.paused_seconds >= 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"pdf_path": Path("missing.pdf")}, "PDF was not found"),
        ({"dpi": 20}, "DPI must be"),
    ],
)
def test_validate_options_rejects_invalid_inputs(
    tmp_path: Path, change: dict[str, object], message: str
) -> None:
    with pytest.raises(ConversionError, match=message):
        validate_options(options(tmp_path, **change))


def test_validate_options_rejects_non_pdf_output_and_missing_css(tmp_path: Path) -> None:
    text_file = tmp_path / "source.txt"
    text_file.write_text("not pdf", encoding="utf-8")
    with pytest.raises(ConversionError, match="must be a PDF"):
        validate_options(options(tmp_path, pdf_path=text_file))

    existing = tmp_path / "result.epub"
    existing.write_text("old", encoding="utf-8")
    with pytest.raises(ConversionError, match="already exists"):
        validate_options(options(tmp_path, epub_path=existing))
    with pytest.raises(ConversionError, match="Stylesheet was not found"):
        validate_options(
            options(
                tmp_path,
                epub_path=tmp_path / "new.epub",
                css_path=tmp_path / "missing.css",
            )
        )


def test_pandoc_command_contains_metadata_resources_and_css(tmp_path: Path) -> None:
    markdown = tmp_path / "work" / "book.md"
    epub = tmp_path / "book.epub"
    css = tmp_path / "reader.css"
    cover = tmp_path / "cover.jpg"
    command = _pandoc_command(
        markdown, epub, BookMetadata("Title", "Author", "Press", "tr"), css, cover
    )
    assert f"--resource-path={markdown.parent}" in command
    assert "--metadata=publisher:Press" in command
    assert f"--css={css}" in command
    assert f"--epub-cover-image={cover}" in command


def test_create_epub_reports_pandoc_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "pdf_to_epub.converter.subprocess.run",
        Mock(return_value=types.SimpleNamespace(returncode=1, stderr="bad input")),
    )
    with pytest.raises(ConversionError, match="bad input"):
        create_epub(tmp_path / "book.md", tmp_path / "book.epub", BookMetadata("Book"), None)

    monkeypatch.setattr(
        "pdf_to_epub.converter.subprocess.run", Mock(side_effect=OSError("missing"))
    )
    with pytest.raises(ConversionError, match="could not be started"):
        create_epub(tmp_path / "book.md", tmp_path / "book.epub", BookMetadata("Book"), None)


def test_create_epub_requires_output_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "pdf_to_epub.converter.subprocess.run",
        Mock(return_value=types.SimpleNamespace(returncode=0, stderr="")),
    )
    with pytest.raises(ConversionError, match="did not create"):
        create_epub(tmp_path / "book.md", tmp_path / "book.epub", BookMetadata("Book"), None)


def test_export_markdown_copies_assets_and_rewrites_links(tmp_path: Path) -> None:
    source = tmp_path / "work" / "book.md"
    assets = source.parent / "assets"
    assets.mkdir(parents=True)
    source.write_text("![Kapak](assets/cover.png)\n", encoding="utf-8")
    (assets / "cover.png").write_bytes(b"image")
    output = tmp_path / "output" / "kitap.md"
    output.parent.mkdir()

    export_markdown(source, assets, output, overwrite=False)

    output_assets = markdown_assets_output_path(output)
    assert output.read_text(encoding="utf-8") == "![Kapak](kitap_assets/cover.png)\n"
    assert (output_assets / "cover.png").read_bytes() == b"image"

    with pytest.raises(ConversionError, match="assets already exist"):
        export_markdown(source, assets, output, overwrite=False)

    (output_assets / "old.png").write_bytes(b"old")
    export_markdown(source, assets, output, overwrite=True)
    assert not (output_assets / "old.png").exists()


def test_create_mobi_uses_calibre_and_checks_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    markdown = tmp_path / "book.md"
    markdown.write_text("# Book", encoding="utf-8")
    mobi = tmp_path / "book.mobi"
    monkeypatch.setattr("pdf_to_epub.converter.find_ebook_convert", lambda: "ebook-convert")

    def fake_epub(
        _markdown: Path,
        epub: Path,
        _metadata: BookMetadata,
        _css: Path | None,
        _cover: Path | None = None,
    ) -> None:
        epub.write_bytes(b"epub")

    def fake_run(command: list[str], **_kwargs: object) -> types.SimpleNamespace:
        assert command[0] == "ebook-convert"
        Path(command[2]).write_bytes(b"mobi")
        return types.SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("pdf_to_epub.converter.create_epub", fake_epub)
    monkeypatch.setattr("pdf_to_epub.converter.subprocess.run", fake_run)
    create_mobi(markdown, mobi, BookMetadata("Book"), None)
    assert mobi.read_bytes() == b"mobi"

    monkeypatch.setattr(
        "pdf_to_epub.converter.subprocess.run",
        Mock(
            return_value=types.SimpleNamespace(returncode=1, stderr="conversion failed", stdout="")
        ),
    )
    with pytest.raises(ConversionError, match="conversion failed"):
        create_mobi(markdown, mobi, BookMetadata("Book"), None)

    monkeypatch.setattr("pdf_to_epub.converter.find_ebook_convert", lambda: None)
    with pytest.raises(ConversionError, match="Calibre"):
        create_mobi(markdown, mobi, BookMetadata("Book"), None)


def test_check_runtime_handles_missing_tools_and_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: None)
    with pytest.raises(ConversionError, match="Pandoc"):
        check_runtime()

    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    with pytest.raises(ConversionError, match="CUDA/ROCm is not available"):
        check_runtime()


def test_check_runtime_only_requires_format_specific_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: None)
    monkeypatch.setitem(sys.modules, "torch", fake_torch(total_gib=8, free_gib=8))
    assert check_runtime("markdown") is None
    with pytest.raises(ConversionError, match="Pandoc"):
        check_runtime("epub")

    monkeypatch.setattr(
        "pdf_to_epub.converter.shutil.which", lambda name: "pandoc" if name == "pandoc" else None
    )
    monkeypatch.setattr("pdf_to_epub.converter.find_ebook_convert", lambda: None)
    with pytest.raises(ConversionError, match="Calibre"):
        check_runtime("mobi")


def test_check_runtime_warns_when_available_vram_is_low(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    monkeypatch.setitem(sys.modules, "torch", fake_torch(total_gib=8, free_gib=5.5))
    warning = check_runtime()
    assert warning is not None
    assert "5.5 GB" in warning
    assert "8.0 GB VRAM available" in warning


def test_check_runtime_rejects_six_gib_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    monkeypatch.setitem(sys.modules, "torch", fake_torch(total_gib=6, free_gib=5.5))
    with pytest.raises(ConversionError, match="does not fit reliably in a 6 GB GPU"):
        check_runtime()


def test_check_runtime_rejects_too_little_available_vram(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    monkeypatch.setitem(sys.modules, "torch", fake_torch(total_gib=8, free_gib=4))
    with pytest.raises(ConversionError, match="not enough free VRAM"):
        check_runtime()


def test_check_runtime_requires_sm120_for_blackwell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    monkeypatch.setitem(
        sys.modules,
        "torch",
        fake_torch(
            total_gib=12,
            free_gib=10,
            capability=(12, 0),
            architectures=["sm_90"],
        ),
    )
    with pytest.raises(ConversionError, match="sm_120"):
        check_runtime()


def test_check_runtime_accepts_rocm_and_does_not_apply_blackwell_cuda_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    rocm_torch = fake_torch(
        total_gib=16,
        free_gib=14,
        capability=(12, 0),
        architectures=["gfx1200"],
        backend="rocm",
    )
    monkeypatch.setitem(sys.modules, "torch", rocm_torch)
    assert accelerator_backend(rocm_torch) == "rocm"
    assert check_runtime() is None

    cuda_torch = fake_torch(total_gib=12, free_gib=10)
    assert accelerator_backend(cuda_torch) == "cuda"


def test_conversion_forwards_options_and_cleans_successful_workdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr("pdf_to_epub.converter.configure_huggingface_cache", lambda _path: True)

    def transform_markdown(**kwargs: object) -> None:
        calls.update(kwargs)
        on_ocr_event = kwargs["on_ocr_event"]
        assert callable(on_ocr_event)
        on_ocr_event(
            types.SimpleNamespace(
                kind=types.SimpleNamespace(name="START"), page_index=2, total_pages=10
            )
        )
        on_ocr_event(
            types.SimpleNamespace(
                kind=types.SimpleNamespace(name="RENDERED"), page_index=2, total_pages=10
            )
        )
        on_ocr_event(
            types.SimpleNamespace(
                kind=types.SimpleNamespace(name="COMPLETE"), page_index=2, total_pages=10
            )
        )
        Path(str(kwargs["markdown_path"])).write_text("hy-\nphen", encoding="utf-8")
        analysis = Path(str(kwargs["analysing_path"]))
        analysis.mkdir(parents=True, exist_ok=True)
        (analysis / "cover.png").write_bytes(b"cover")

    fake_module = types.SimpleNamespace(transform_markdown=transform_markdown)
    monkeypatch.setitem(sys.modules, "pdf_craft", fake_module)

    def fake_create(
        markdown_path: Path,
        epub_path: Path,
        metadata: BookMetadata,
        css_path: Path | None,
        cover_path: Path | None,
    ) -> None:
        assert markdown_path.read_text(encoding="utf-8") == "hyphen"
        assert metadata.title == "A Book"
        assert css_path is None
        assert cover_path is not None
        assert cover_path.read_bytes() == b"cover"
        epub_path.write_bytes(b"epub")

    monkeypatch.setattr("pdf_to_epub.converter.create_epub", fake_create)
    progress: list[ConversionProgress] = []
    pause_controller = ConversionPauseController()
    result = convert_pdf(
        options(tmp_path, ocr_size="base", dpi=144),
        progress.append,
        pause_controller,
    )

    assert result.epub_path.read_bytes() == b"epub"
    assert result.hyphenation_fixes == 1
    assert not result.work_dir.exists()
    assert calls["ocr_size"] == "base"
    assert calls["dpi"] == 144
    assert calls["includes_cover"] is True
    assert calls["aborted"] == pause_controller.wait_if_paused
    assert len(progress) == 8
    assert progress[2] == ConversionProgress(
        "Rendering PDF page", "ocr", current_page=2, total_pages=10, completed_pages=1
    )
    assert progress[2].percentage == 10
    assert progress[3].message == "Loading OCR model and processing PDF page"
    assert progress[3].percentage == 10
    assert progress[4].message == "Completed PDF page"
    assert progress[4].percentage == 20


def test_conversion_can_publish_markdown_with_assets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.configure_huggingface_cache", lambda _path: True)

    def transform_markdown(**kwargs: object) -> None:
        assert kwargs["includes_cover"] is False
        markdown = Path(str(kwargs["markdown_path"]))
        assets = Path(str(kwargs["markdown_assets_path"]))
        assets.mkdir(parents=True)
        (assets / "page.png").write_bytes(b"image")
        markdown.write_text("ke-\nlimeler\n\n![](assets/page.png)", encoding="utf-8")

    monkeypatch.setitem(
        sys.modules,
        "pdf_craft",
        types.SimpleNamespace(transform_markdown=transform_markdown),
    )
    selected = options(tmp_path, epub_path=tmp_path / "result.md")
    result = convert_pdf(selected)

    assert result.output_format == "markdown"
    assert "kelimeler" in result.output_path.read_text(encoding="utf-8")
    assert "result_assets/page.png" in result.output_path.read_text(encoding="utf-8")
    assert (tmp_path / "result_assets" / "page.png").read_bytes() == b"image"


def test_conversion_can_publish_mobi(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.configure_huggingface_cache", lambda _path: True)

    def transform_markdown(**kwargs: object) -> None:
        assert kwargs["includes_cover"] is True
        Path(str(kwargs["markdown_path"])).write_text("# Book", encoding="utf-8")
        analysis = Path(str(kwargs["analysing_path"]))
        analysis.mkdir(parents=True, exist_ok=True)
        (analysis / "cover.png").write_bytes(b"cover")

    def fake_mobi(
        _markdown: Path,
        mobi: Path,
        _metadata: BookMetadata,
        _css: Path | None,
        cover: Path | None,
    ) -> None:
        assert cover is not None
        assert cover.read_bytes() == b"cover"
        mobi.write_bytes(b"mobi")

    monkeypatch.setitem(
        sys.modules,
        "pdf_craft",
        types.SimpleNamespace(transform_markdown=transform_markdown),
    )
    monkeypatch.setattr("pdf_to_epub.converter.create_mobi", fake_mobi)
    selected = options(tmp_path, epub_path=tmp_path / "result.mobi")
    progress: list[ConversionProgress] = []
    result = convert_pdf(selected, progress.append)

    assert result.output_format == "mobi"
    assert result.output_path.read_bytes() == b"mobi"
    assert progress[-1].message == "Building MOBI with Calibre"


def test_conversion_progress_percentage_handles_unknown_and_bounds() -> None:
    assert ConversionProgress("Preparing", "models").percentage is None
    assert ConversionProgress("Reading", "ocr", 1, 0, 0).percentage is None
    assert ConversionProgress("Reading", "ocr", 1, 10, -1).percentage == 0
    assert ConversionProgress("Done", "ocr", 10, 10, 12).percentage == 100


def test_conversion_keeps_intermediates_and_wraps_upstream_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.configure_huggingface_cache", lambda _path: True)
    root_error = RuntimeError("CUDA out of memory")
    wrapped_error = RuntimeError("Failed to extract page 1 layout at stage 1")
    wrapped_error.__cause__ = root_error
    fake_module = types.SimpleNamespace(
        transform_markdown=lambda **_kwargs: (_ for _ in ()).throw(wrapped_error),
    )
    monkeypatch.setitem(sys.modules, "pdf_craft", fake_module)
    selected = options(tmp_path, keep_intermediates=True)
    with pytest.raises(ConversionError, match="Failed to extract.*CUDA out of memory"):
        convert_pdf(selected)
    assert any((tmp_path / "work").iterdir())
