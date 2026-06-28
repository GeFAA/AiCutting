from pathlib import Path

from aicutting.core.models import LocationTitle
from aicutting.render.titles import (
    build_drawtext_filter,
    build_title_overlay,
    escape_drawtext_text,
)

_FPS = 59.94005994005994


def _reveal_title() -> LocationTitle:
    return LocationTitle(title="Iceland", subtitle="June 2025", confidence=0.98)


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


def test_build_title_overlay_emerges_text_from_behind_terrain() -> None:
    graph = build_title_overlay(_reveal_title(), None, 1280, 720, _FPS)

    # The title and subtitle are drawn.
    assert "text='Iceland'" in graph
    assert "text='June 2025'" in graph
    # A feathered luma mask is derived from the video under the text.
    assert "format=gray" in graph
    assert "lut=c0=" in graph
    assert "gblur=" in graph
    # The mask gates the text alpha, which is merged back and composited over the base.
    assert "alphaextract" in graph
    assert "blend=all_expr=" in graph
    assert "alphamerge" in graph
    assert "overlay=eof_action=pass[vout]" in graph
    # The block rises (eased) and fades in fast -- by ~1s, not the old slow 2-3.8s.
    assert "(t-0.4)/0.6" in graph  # the fast rise smoothstep
    assert "alpha='if(lt(t,0.4),0," in graph  # the fast fade-in
    assert "lt(t,2),0" not in graph  # not the old slow fade


def test_unknown_reveal_falls_back_to_emerge() -> None:
    out = build_title_overlay(_reveal_title(), None, 1920, 1080, _FPS, style="does-not-exist")
    assert out.endswith("overlay=eof_action=pass[vout]")
    assert "lut=c0=" in out  # the emerge luma occlusion


def test_each_reveal_emerges_from_behind_the_terrain() -> None:
    for style in ("emerge", "slide", "drop", "wipe"):
        graph = build_title_overlay(_reveal_title(), None, 1920, 1080, _FPS, style=style)
        assert "[vbase]format=yuv420p,split=2[base][src]" in graph  # format pinned before split
        assert "blend=all_expr=" in graph  # the terrain occlusion blend
        assert graph.endswith("overlay=eof_action=pass[vout]")


def test_reveals_differ_in_motion() -> None:
    graphs = {
        s: build_title_overlay(_reveal_title(), None, 1920, 1080, _FPS, style=s)
        for s in ("emerge", "slide", "drop", "wipe")
    }
    assert len(set(graphs.values())) == 4  # four distinct filtergraphs


def test_build_title_overlay_pins_format_before_split_to_keep_color() -> None:
    # split emits one negotiated format to both branches; without pinning yuv420p first the gray
    # mask branch desaturates the base when [vbase] arrives from an xfade chain.
    graph = build_title_overlay(_reveal_title(), None, 1280, 720, _FPS)
    assert "[vbase]format=yuv420p,split=2[base][src]" in graph


def test_build_title_overlay_scales_geometry_with_height() -> None:
    small = build_title_overlay(_reveal_title(), None, 1280, 720, _FPS)
    large = build_title_overlay(_reveal_title(), None, 3840, 2160, _FPS)
    assert "s=1280x720" in small
    assert "fontsize=65" in small  # round(720 / 11)
    assert "s=3840x2160" in large
    assert "fontsize=196" in large  # round(2160 / 11)


def test_build_title_overlay_horizon_fallback_uses_a_horizon_line_mask() -> None:
    graph = build_title_overlay(_reveal_title(), None, 1280, 720, _FPS, style="horizon")
    assert "geq=lum=" in graph  # a fixed horizon gradient, not the per-frame video luma
    assert "lut=c0=" not in graph
    assert "text='Iceland'" in graph
    assert "overlay=eof_action=pass[vout]" in graph


def test_build_title_overlay_plain_fallback_is_the_faded_lower_third() -> None:
    title = _reveal_title()
    graph = build_title_overlay(title, None, 1280, 720, _FPS, style="plain")
    assert graph == f"[vbase]{build_drawtext_filter(title, None)}[vout]"
    assert "y=h-200" in graph  # the lower-third caption, not the emerging centre block
    assert "split" not in graph  # no masking pipeline


def test_build_title_overlay_escapes_colon_and_apostrophe_in_reveal() -> None:
    title = LocationTitle(title="O'Hara: Bay", subtitle=None, confidence=0.9)
    graph = build_title_overlay(title, None, 1280, 720, _FPS)
    assert escape_drawtext_text("O'Hara: Bay") in graph
