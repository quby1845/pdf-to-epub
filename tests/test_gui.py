from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pdf_to_epub.converter import ConversionPauseController
from pdf_to_epub.gui import PdfToEpubApp


class FakeWidget:
    def __init__(self) -> None:
        self.config: dict[str, object] = {}
        self.calls: list[tuple[str, object]] = []

    def configure(self, **kwargs: object) -> None:
        self.config.update(kwargs)

    def start(self, interval: int) -> None:
        self.calls.append(("start", interval))

    def stop(self) -> None:
        self.calls.append(("stop", None))


class FakeVar:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


def test_scrolling_over_selector_scrolls_page_and_stops_combobox_binding() -> None:
    scrolls: list[tuple[int, str]] = []
    canvas = SimpleNamespace(
        bbox=lambda _target: (0, 0, 800, 1200),
        winfo_height=lambda: 600,
        yview_scroll=lambda amount, unit: scrolls.append((amount, unit)),
    )
    app = object.__new__(PdfToEpubApp)
    app.content_canvas = canvas

    result = app._scroll_over_selector(SimpleNamespace(delta=-120))

    assert result == "break"
    assert scrolls == [(1, "units")]


def test_pause_button_pauses_and_resumes_the_same_conversion() -> None:
    statuses: list[tuple[str, str]] = []
    app = object.__new__(PdfToEpubApp)
    app.ui_language = "tr"
    app.converting = True
    app.paused = False
    app.pause_controller = ConversionPauseController()
    app.last_progress = None
    app.pause_button = FakeWidget()
    app.progress = FakeWidget()
    app.theme = SimpleNamespace(ink="black")
    app._icon = lambda name, _color: name
    app._set_status = lambda message, kind="neutral": statuses.append((message, kind))

    app._toggle_pause()

    assert app.paused is True
    assert app.pause_controller.is_paused is True
    assert app.pause_button.config["text"] == "Devam et"
    assert app.progress.calls[-1] == ("stop", None)
    assert statuses[-1][1] == "warning"

    app._toggle_pause()

    assert app.paused is False
    assert app.pause_controller.is_paused is False
    assert app.pause_button.config["text"] == "Duraklat"
    assert app.progress.calls[-1] == ("start", 12)


def test_language_toggle_localizes_defaults_and_preserves_choices(monkeypatch) -> None:
    app = object.__new__(PdfToEpubApp)
    app.converting = False
    app.ui_language = "tr"
    app.model_var = FakeVar("Small — 640 px / tahmini ≈7,5 GB VRAM")
    app.output_format_var = FakeVar("Markdown — düzenlenebilir metin (.md)")
    app.model_help_var = FakeVar("")
    app.author_var = FakeVar("Bilinmiyor")
    app.language_var = FakeVar("tr")
    app.pdf_var = FakeVar("")
    app.selected_file_var = FakeVar("Henüz PDF seçilmedi")
    app.selected_file_detail_var = FakeVar(
        "Bilgisayarınızdan dönüştürmek istediğiniz kitabı seçin."
    )
    app.status_var = FakeVar("Bir PDF seçerek başlayın.")
    rebuilt: list[bool] = []
    app._rebuild_ui = lambda: rebuilt.append(True)
    monkeypatch.setattr("pdf_to_epub.gui.save_language_preference", lambda _language: None)

    app._toggle_language()

    assert app.ui_language == "en"
    assert app.model_var.get() == "Small — 640 px / estimated ≈7.5 GB VRAM"
    assert app.output_format_var.get() == "Markdown — editable text (.md)"
    assert app.author_var.get() == "Unknown"
    assert app.language_var.get() == "en"
    assert app.selected_file_var.get() == "No PDF selected yet"
    assert app.status_var.get() == "Start by choosing a PDF."
    assert rebuilt == [True]


def test_choose_file_for_koreader_accepts_any_regular_file(tmp_path: Path, monkeypatch) -> None:
    selected = tmp_path / "archive.custom"
    selected.write_bytes(b"payload")
    app = object.__new__(PdfToEpubApp)
    app.ui_language = "en"
    opened: list[tuple[object, Path]] = []
    monkeypatch.setattr(
        "pdf_to_epub.gui.filedialog.askopenfilename",
        lambda **_kwargs: str(selected),
    )
    monkeypatch.setattr(
        "pdf_to_epub.gui.KOReaderSendDialog",
        lambda owner, path: opened.append((owner, path)),
    )

    app._choose_file_for_koreader()

    assert opened == [(app, selected)]
