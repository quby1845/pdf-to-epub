from __future__ import annotations

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
