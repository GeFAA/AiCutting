from collections.abc import Callable
from pathlib import Path

from aicutting.core.models import LocationTitle

_FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
)

# Bold siblings of the discovered fonts. The hero title reads better in a heavier weight while
# the subtitle keeps the regular face; if a bold file is missing we fall back to the regular one.
_BOLD_NAMES = {
    "arial.ttf": "arialbd.ttf",
    "segoeui.ttf": "segoeuib.ttf",
    "DejaVuSans.ttf": "DejaVuSans-Bold.ttf",
    "Arial.ttf": "Arial Bold.ttf",
}


def escape_drawtext_text(text: str) -> str:
    # Produce a value safe to wrap in ffmpeg single quotes. Inside those quotes ':'
    # still needs '\:' and a literal "'" cannot be backslash-escaped, so it is written
    # as the close/escaped-quote/reopen splice "'\''".
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")


def build_drawtext_filter(title: LocationTitle, font_path: Path | None) -> str:
    # The plain, ultimate-fallback lower-third: a tasteful caption that simply fades in over the
    # opening shot. `build_title_overlay(style="plain")` wraps this when the cinematic reveal is
    # not wanted.
    # fontfile MUST precede text: ffmpeg drops a fontfile that follows an apostrophe
    # splice in the text value and then fails to load any font.
    font = f"fontfile='{escape_drawtext_text(font_path.as_posix())}':" if font_path else ""
    fade = _intro_fade()
    main = (
        "drawtext="
        f"{font}text='{escape_drawtext_text(title.title)}':fontsize=56:fontcolor=white:"
        f"x=80:y=h-200:shadowcolor=black:shadowx=2:shadowy=2:alpha='{fade}'"
    )
    subtitle = title.subtitle or ""
    if not subtitle:
        return main
    sub = (
        "drawtext="
        f"{font}text='{escape_drawtext_text(subtitle)}':fontsize=32:fontcolor=white:"
        f"x=82:y=h-132:shadowcolor=black:shadowx=2:shadowy=2:alpha='{fade}'"
    )
    return f"{main},{sub}"


def build_title_overlay(
    title: LocationTitle,
    font_path: Path | None,
    width: int,
    height: int,
    fps: float,
    *,
    style: str = "emerge",
) -> str:
    """Return a filter sub-graph that consumes ``[vbase]`` and produces ``[vout]``.

    ``style`` selects the reveal:

    * ``"emerge"`` (default) - the cinematic luma-occluded reveal where the dark foreground
      terrain hides the title and the title rises out from behind the ridge.
    * ``"horizon"`` - the robust fallback: the same rise+fade but masked by a fixed horizon
      line instead of the per-frame video luma (use when luma masking looks bad on a shot).
    * ``"plain"`` - the ultimate fallback: the flat faded lower-third of
      :func:`build_drawtext_filter`.
    """
    if style == "plain":
        return f"[vbase]{build_drawtext_filter(title, font_path)}[vout]"
    if style == "horizon":
        return _emerge_subgraph(title, font_path, width, height, fps, mask="horizon")
    reveal = _REVEALS.get(style, _emerge_subgraph)
    return reveal(title, font_path, width, height, fps)


def _reveal_subgraph(
    title: LocationTitle,
    font_path: Path | None,
    width: int,
    height: int,
    fps: float,
    *,
    y_of: Callable[[int], str],
    mask_mid: str | None = None,
    reveal_mask: str | None = None,
) -> str:
    # The shared reveal assembler. Geometry scales with height so the look holds from the 720p
    # preview to the 4K master. ``y_of`` gives each reveal its own motion; ``reveal_mask`` is an
    # optional extra mask on the text alpha (the wipe); ``mask_mid`` overrides the terrain mask
    # (the horizon line). All reveals keep the luma occlusion -- the title emerges from the terrain.
    title_size = round(height / 11)
    subtitle_size = round(height / 26)
    title_y = round(height * 0.34)
    subtitle_y = title_y + title_size + round(height * 0.018)
    shadow = max(1, round(height / 360))
    sigma = max(1.0, height / 360)
    window_s = 9.0
    fade = _intro_fade()
    # Occlusion is full strength through the emergence, then relaxes sooner than before so the
    # settled title stays legible without the long slow hold that read as boring.
    relax = _smoothstep("T", 2.2, 1.2)
    blend_expr = f"A*(B+(255-B)*{relax})/255"

    bold = _bold_variant(font_path)
    draws = [_drawtext(title.title, bold, title_size, shadow, y_of(title_y), fade)]
    if title.subtitle:
        draws.append(
            _drawtext(title.subtitle, font_path, subtitle_size, shadow, y_of(subtitle_y), fade)
        )
    text_chain = ",".join(draws)
    # Map the video luma to a soft silhouette: dark terrain -> 0 (hide), bright sky -> 255 (show).
    silhouette = mask_mid or "lut=c0='255*clip((val-70)/60,0,1)'"
    extra = f",{reveal_mask}" if reveal_mask else ""

    text_layer = (
        f"color=c=black@0:s={width}x{height}:d={_g(window_s)}:r={fps},"
        f"format=rgba,{text_chain}{extra}[txtcol]"
    )
    segments = [
        # Pin the format before the split: split emits one negotiated format to both branches,
        # and without this the gray mask branch drags the negotiation and the base loses its
        # chroma (the whole picture turns grayscale) when [vbase] comes from xfade.
        "[vbase]format=yuv420p,split=2[base][src]",
        f"[src]format=gray,{silhouette},gblur=sigma={_g(sigma)},"
        f"trim=end={_g(window_s)},setpts=PTS-STARTPTS[occ]",
        text_layer,
        "[txtcol]split[txtc1][txtc2]",
        "[txtc2]alphaextract[ta]",
        f"[ta][occ]blend=all_expr='{blend_expr}':shortest=1[na]",
        "[txtc1][na]alphamerge[tl]",
        "[base][tl]overlay=eof_action=pass[vout]",
    ]
    return ";".join(segments)


def _emerge_subgraph(
    title: LocationTitle, font_path: Path | None, width: int, height: int, fps: float,
    *, mask: str = "luma",
) -> str:
    # The hero reveal: the title rises a touch out from behind the terrain, settling fast (~1s).
    if mask == "horizon":
        line = round(height * 0.52)
        feather = round(height * 0.06)
        horizon = f"geq=lum='255*clip(({line}-Y)/{feather},0,1)'"
        rise = round(height * 0.11)
        return _reveal_subgraph(
            title, font_path, width, height, fps,
            y_of=lambda y: f"{y}+{rise}*(1-{_smoothstep('t', 0.4, 0.6)})", mask_mid=horizon,
        )
    rise = round(height * 0.11)
    return _reveal_subgraph(
        title, font_path, width, height, fps,
        y_of=lambda y: f"{y}+{rise}*(1-{_smoothstep('t', 0.4, 0.6)})",
    )


def _slide_subgraph(
    title: LocationTitle, font_path: Path | None, width: int, height: int, fps: float
) -> str:
    # Slides up from lower in the frame -- a longer, more pronounced travel than emerge.
    off = round(height * 0.22)
    return _reveal_subgraph(
        title, font_path, width, height, fps,
        y_of=lambda y: f"{y}+{off}*(1-{_smoothstep('t', 0.4, 0.7)})",
    )


def _drop_subgraph(
    title: LocationTitle, font_path: Path | None, width: int, height: int, fps: float
) -> str:
    # Drops down from above into place.
    off = round(height * 0.14)
    return _reveal_subgraph(
        title, font_path, width, height, fps,
        y_of=lambda y: f"{y}-{off}*(1-{_smoothstep('t', 0.4, 0.6)})",
    )


def _wipe_subgraph(
    title: LocationTitle, font_path: Path | None, width: int, height: int, fps: float
) -> str:
    # Stationary text revealed by a soft vertical edge sweeping left -> right over ~0.35..1.2s.
    edge = f"({width}*1.3*clip((T-0.35)/0.85,0,1)-{width}*0.15)"
    feather = f"({width}*0.1)"
    wipe = (
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
        f"a='alpha(X,Y)*clip(({edge}-X)/{feather},0,1)'"
    )
    return _reveal_subgraph(
        title, font_path, width, height, fps, y_of=lambda y: str(y), reveal_mask=wipe
    )


_REVEALS: dict[str, Callable[[LocationTitle, Path | None, int, int, float], str]] = {
    "emerge": _emerge_subgraph,
    "slide": _slide_subgraph,
    "drop": _drop_subgraph,
    "wipe": _wipe_subgraph,
}


def _drawtext(
    text: str,
    font_path: Path | None,
    fontsize: int,
    shadow: int,
    y_expr: str,
    alpha_expr: str,
) -> str:
    # fontfile MUST precede text (see build_drawtext_filter). The text is horizontally centred and
    # carries a soft shadow so white glyphs stay readable over both bright sky and dark terrain.
    font = f"fontfile='{escape_drawtext_text(font_path.as_posix())}':" if font_path else ""
    # A crisp dark outline keeps the title premium and legible over bright sky or dark terrain;
    # the soft shadow underneath gives it depth as it emerges.
    border = max(2, round(fontsize / 26))
    return (
        "drawtext="
        f"{font}text='{escape_drawtext_text(text)}':fontcolor=white:fontsize={fontsize}:"
        f"borderw={border}:bordercolor=black@0.55:"
        f"shadowcolor=black@0.5:shadowx={shadow}:shadowy={shadow}:"
        f"x=(w-text_w)/2:y='{y_expr}':alpha='{alpha_expr}'"
    )


def _smoothstep(var: str, start: float, duration: float) -> str:
    # Hermite smoothstep of `var` ramped over [start, start+duration], clamped to 0..1.
    p = f"clip(({var}-{_g(start)})/{_g(duration)},0,1)"
    return f"({p}*{p}*(3-2*{p}))"


def _g(value: float) -> str:
    return f"{value:g}"


def _intro_fade() -> str:
    # Invisible, fade in 0.4->1.0 s (punchy), hold, fade out 7->8 s. Single-quoted in the filter so
    # the commas inside the expression do not split the drawtext options.
    return "if(lt(t,0.4),0,if(lt(t,1),(t-0.4)/0.6,if(lt(t,7),1,if(lt(t,8),8-t,0))))"


def _bold_variant(font_path: Path | None) -> Path | None:
    if font_path is None:
        return None
    bold_name = _BOLD_NAMES.get(font_path.name)
    if bold_name is not None:
        candidate = font_path.with_name(bold_name)
        if candidate.exists():
            return candidate
    return font_path


def discover_font() -> Path | None:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None
