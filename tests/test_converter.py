from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import Mock

import pytest

from pdf_to_epub.converter import (
    BookMetadata,
    ConversionError,
    ConversionOptions,
    _pandoc_command,
    check_runtime,
    convert_pdf,
    create_epub,
    fix_hyphenation,
    fix_hyphenation_file,
    sanitize_filename,
    suggested_output_name,
    validate_options,
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


def test_fix_hyphenation_only_merges_lowercase_continuations(tmp_path: Path) -> None:
    text = "popu-\nlar and bi- lingual but ISO-\nStandard"
    fixed, count = fix_hyphenation(text)
    assert fixed == "popular and bilingual but ISO-\nStandard"
    assert count == 2

    markdown = tmp_path / "book.md"
    markdown.write_text("hel-\nlo", encoding="utf-8")
    assert fix_hyphenation_file(markdown) == 1
    assert markdown.read_text(encoding="utf-8") == "hello"


def test_fix_hyphenation_file_requires_generated_markdown(tmp_path: Path) -> None:
    with pytest.raises(ConversionError, match="Markdown was not found"):
        fix_hyphenation_file(tmp_path / "missing.md")


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
    command = _pandoc_command(markdown, epub, BookMetadata("Title", "Author", "Press", "tr"), css)
    assert f"--resource-path={markdown.parent}" in command
    assert "--metadata=publisher:Press" in command
    assert f"--css={css}" in command


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


def test_check_runtime_handles_missing_tools_and_cpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: None)
    with pytest.raises(ConversionError, match="Pandoc"):
        check_runtime()

    monkeypatch.setattr("pdf_to_epub.converter.shutil.which", lambda _name: "pandoc")
    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    assert "CUDA is not available" in check_runtime()


def test_conversion_forwards_options_and_cleans_successful_workdir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: dict[str, object] = {}

    def transform_markdown(**kwargs: object) -> None:
        calls.update(kwargs)
        Path(str(kwargs["markdown_path"])).write_text("hy-\nphen", encoding="utf-8")

    fake_module = types.SimpleNamespace(
        predownload_models=lambda **kwargs: calls.update(kwargs),
        transform_markdown=transform_markdown,
    )
    monkeypatch.setitem(sys.modules, "pdf_craft", fake_module)

    def fake_create(
        markdown_path: Path, epub_path: Path, metadata: BookMetadata, css_path: Path | None
    ) -> None:
        assert markdown_path.read_text(encoding="utf-8") == "hyphen"
        assert metadata.title == "A Book"
        assert css_path is None
        epub_path.write_bytes(b"epub")

    monkeypatch.setattr("pdf_to_epub.converter.create_epub", fake_create)
    progress: list[str] = []
    result = convert_pdf(options(tmp_path, ocr_size="base", dpi=144), progress.append)

    assert result.epub_path.read_bytes() == b"epub"
    assert result.hyphenation_fixes == 1
    assert not result.work_dir.exists()
    assert calls["ocr_size"] == "base"
    assert calls["dpi"] == 144
    assert len(progress) == 4


def test_conversion_keeps_intermediates_and_wraps_upstream_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake_module = types.SimpleNamespace(
        predownload_models=lambda **_kwargs: None,
        transform_markdown=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("OCR failed")),
    )
    monkeypatch.setitem(sys.modules, "pdf_craft", fake_module)
    selected = options(tmp_path, keep_intermediates=True)
    with pytest.raises(ConversionError, match="OCR failed"):
        convert_pdf(selected)
    assert any((tmp_path / "work").iterdir())
