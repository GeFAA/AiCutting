from pathlib import Path

from aicutting.core.models import LocationTitle
from aicutting.render.titles import build_drawtext_filter, escape_drawtext_text


def test_escape_drawtext_text_handles_special_characters() -> None:
    assert escape_drawtext_text("Madeira: Coast's Edge") == "Madeira\\: Coast\\'s Edge"


def test_build_drawtext_filter_uses_title_and_subtitle() -> None:
    title = LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.9)

    filter_text = build_drawtext_filter(title, font_path=Path("C:/Windows/Fonts/arial.ttf"))

    assert "drawtext=" in filter_text
    assert "Madeira Coast" in filter_text
    assert "Portugal" in filter_text
