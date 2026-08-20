from __future__ import annotations

from types import SimpleNamespace

from pdf_to_epub.gui import PdfToEpubApp


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
