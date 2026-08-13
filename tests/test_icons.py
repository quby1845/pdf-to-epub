from __future__ import annotations

import pytest

from pdf_to_epub.icons import _xbm_data, icon_names


def test_icon_set_contains_every_desktop_action() -> None:
    assert {
        "app",
        "book",
        "check",
        "external",
        "file",
        "folder",
        "info",
        "moon",
        "play",
        "save",
        "scan",
        "shield",
        "sliders",
        "sparkles",
        "sun",
        "warning",
    } <= set(icon_names())


def test_xbm_encoder_builds_tk_bitmap_data() -> None:
    data = _xbm_data(("10000000", "00000001"))

    assert "#define icon_width 8" in data
    assert "#define icon_height 2" in data
    assert "0x01, 0x80" in data


@pytest.mark.parametrize(
    "rows",
    [(), ("10", "1"), ("10", "2x")],
)
def test_xbm_encoder_rejects_invalid_patterns(rows: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        _xbm_data(rows)
