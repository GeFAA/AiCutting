from pathlib import Path

from aicutting.core.models import LocationTitle
from aicutting.render.titles import build_drawtext_filter, escape_drawtext_text


def test_escape_drawtext_text_escapes_colon_and_apostrophe_for_ffmpeg() -> None:
    # Inside an ffmpeg single-quoted value a ':' must be written '\:' (even when quoted),
    # and a literal "'" must use the close/escaped-quote/reopen splice "'\''".
    assert escape_drawtext_text("Madeira: Coast's Edge") == "Madeira\\: Coast'\\''s Edge"


def test_build_drawtext_filter_orders_fontfile_before_text() -> None:
    title = LocationTitle(title="O'Hara: Bay", subtitle=None, confidence=0.9)

    filter_text = build_drawtext_filter(title, font_path=Path("C:/Windows/Fonts/arial.ttf"))

    font_marker = "fontfile='C\\:/Windows/Fonts/arial.ttf'"
    text_marker = "text='O'\\''Hara\\: Bay'"
    assert font_marker in filter_text
    assert text_marker in filter_text
    # ffmpeg drops a fontfile placed after an apostrophe splice, so fontfile must lead.
    assert filter_text.index(font_marker) < filter_text.index(text_marker)


def test_build_drawtext_filter_uses_title_and_subtitle() -> None:
    title = LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.9)

    filter_text = build_drawtext_filter(title, font_path=Path("C:/Windows/Fonts/arial.ttf"))

    assert "drawtext=" in filter_text
    assert "Madeira Coast" in filter_text
    assert "Portugal" in filter_text
