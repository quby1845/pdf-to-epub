from __future__ import annotations

from pathlib import Path

import pytest

from pdf_to_epub import cli
from pdf_to_epub.converter import ConversionError, ConversionProgress, ConversionResult


def test_noninteractive_cli_builds_expected_options(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF")
    captured = {}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "check_runtime", lambda: None)

    def fake_convert(options, progress):
        captured["options"] = options
        return ConversionResult(options.epub_path, tmp_path / "work", 1.25, 3, False)

    monkeypatch.setattr(cli, "convert_pdf", fake_convert)
    result = cli.main([str(pdf), "--title", "My Book", "--ocr-size", "small", "--dpi", "144"])

    assert result == 0
    assert captured["options"].ocr_size == "small"
    assert captured["options"].dpi == 144
    assert captured["options"].metadata.title == "My Book"
    assert "EPUB created" in capsys.readouterr().out


def test_cli_reports_conversion_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF")
    monkeypatch.setattr(cli, "check_runtime", lambda: None)
    monkeypatch.setattr(
        cli, "convert_pdf", lambda *_args, **_kwargs: (_ for _ in ()).throw(ConversionError("boom"))
    )
    assert cli.main([str(pdf)]) == 1
    assert "boom" in capsys.readouterr().err


def test_select_pdf_handles_single_multiple_and_invalid_choice(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(ConversionError, match="No PDF"):
        cli._select_pdf(tmp_path / "empty")

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    first = input_dir / "a.pdf"
    first.write_bytes(b"a")
    assert cli._select_pdf(input_dir) == first

    second = input_dir / "b.pdf"
    second.write_bytes(b"b")
    answers = iter(["x", "3", "2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert cli._select_pdf(input_dir) == second


def test_interactive_metadata_uses_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    answers = iter(["", "", "Publisher", "tr"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    args = cli.build_parser().parse_args([])
    metadata = cli._interactive_metadata(tmp_path / "book.pdf", args)
    assert metadata.title == "book"
    assert metadata.author == "Unknown"
    assert metadata.publisher == "Publisher"
    assert metadata.language == "tr"


def test_cli_prints_page_progress(capsys: pytest.CaptureFixture[str]) -> None:
    cli._progress(ConversionProgress("Reading PDF page", "ocr", 84, 327, 83))
    assert "Page 84/327 (25%)" in capsys.readouterr().out
