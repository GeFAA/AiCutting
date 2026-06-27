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
    mask = "horizon" if style == "horizon" else "luma"
    return _emerge_subgraph(title, font_path, width, height, fps, mask=mask)


def _emerge_subgraph(
    title: LocationTitle,
    font_path: Path | None,
    width: int,
    height: int,
    fps: float,
    *,
    mask: str,
) -> str:
    # Geometry scales with the frame height so the look holds at the 1280x720 preview and the
    # 3840x2160 master alike. The title block sits in the upper-middle straddling the horizon so
    # that it can rise out of the terrain rather than float in the clear lower third.
    title_size = round(height / 11)
    subtitle_size = round(height / 26)
    title_y = round(height * 0.34)
    subtitle_y = title_y + title_size + round(height * 0.018)
    rise = round(height * 0.11)
    shadow = max(1, round(height / 360))
    sigma = max(1.0, height / 360)
    window_s = 9.0

    # The block starts `rise` px lower (deeper behind the terrain) and eases up to rest by ~t=3.8.
    rise_term = f"{rise}*(1-{_smoothstep('t', 2.0, 1.8)})"
    fade = _intro_fade()
    # Occlusion is full strength through the emergence, then relaxes (T = blend timestamp) so the
    # settled title stays fully legible even when it ends up over dark ground or after a cut.
    relax = _smoothstep("T", 4.5, 1.5)
    blend_expr = f"A*(B+(255-B)*{relax})/255"

    bold = _bold_variant(font_path)
    draws = [_drawtext(title.title, bold, title_size, shadow, f"{title_y}+{rise_term}", fade)]
    subtitle = title.subtitle or ""
    if subtitle:
        draws.append(
            _drawtext(subtitle, font_path, subtitle_size, shadow, f"{subtitle_y}+{rise_term}", fade)
        )
    text_chain = ",".join(draws)

    if mask == "horizon":
        line = round(height * 0.52)
        feather = round(height * 0.06)
        mask_mid = f"geq=lum='255*clip(({line}-Y)/{feather},0,1)'"
    else:
        # Map the video luma to a soft silhouette: dark terrain -> 0 (hide), bright sky -> 255
        # (show), with a feathered edge over luma 70..130 that gblur softens further.
        mask_mid = "lut=c0='255*clip((val-70)/60,0,1)'"

    segments = [
        # Pin the format before the split: split emits one negotiated format to both branches,
        # and without this the gray mask branch drags the negotiation and the base loses its
        # chroma (the whole picture turns grayscale) when [vbase] comes from xfade.
        "[vbase]format=yuv420p,split=2[base][src]",
        f"[src]format=gray,{mask_mid},gblur=sigma={_g(sigma)},"
        f"trim=end={_g(window_s)},setpts=PTS-STARTPTS[occ]",
        f"color=c=black@0:s={width}x{height}:d={_g(window_s)}:r={fps},format=rgba,{text_chain}[txtcol]",
        "[txtcol]split[txtc1][txtc2]",
        "[txtc2]alphaextract[ta]",
        f"[ta][occ]blend=all_expr='{blend_expr}':shortest=1[na]",
        "[txtc1][na]alphamerge[tl]",
        "[base][tl]overlay=eof_action=pass[vout]",
    ]
    return ";".join(segments)


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
    return (
        "drawtext="
        f"{font}text='{escape_drawtext_text(text)}':fontcolor=white:fontsize={fontsize}:"
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
    # Invisible, fade in 2->3 s, hold, fade out 7->8 s. Single-quoted in the filter so the
    # commas inside the expression do not split the drawtext options.
    return "if(lt(t,2),0,if(lt(t,3),t-2,if(lt(t,7),1,if(lt(t,8),8-t,0))))"


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
