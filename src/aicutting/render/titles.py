from pathlib import Path

from aicutting.core.models import LocationTitle

_FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/Library/Fonts/Arial.ttf"),
)


def escape_drawtext_text(text: str) -> str:
    # Produce a value safe to wrap in ffmpeg single quotes. Inside those quotes ':'
    # still needs '\:' and a literal "'" cannot be backslash-escaped, so it is written
    # as the close/escaped-quote/reopen splice "'\''".
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")


def build_drawtext_filter(title: LocationTitle, font_path: Path | None) -> str:
    # fontfile MUST precede text: ffmpeg drops a fontfile that follows an apostrophe
    # splice in the text value and then fails to load any font.
    font = f"fontfile='{escape_drawtext_text(font_path.as_posix())}':" if font_path else ""
    fade = _intro_fade()  # a tasteful lower-third that fades in over the opening shot
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


def _intro_fade() -> str:
    # Invisible, fade in 2->3 s, hold, fade out 7->8 s. Single-quoted in the filter so the
    # commas inside the expression do not split the drawtext options.
    return "if(lt(t,2),0,if(lt(t,3),t-2,if(lt(t,7),1,if(lt(t,8),8-t,0))))"


def discover_font() -> Path | None:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None
