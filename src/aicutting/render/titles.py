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
    main = (
        "drawtext="
        f"{font}text='{escape_drawtext_text(title.title)}':fontsize=54:fontcolor=white:"
        "x=80:y=h-190:shadowcolor=black:shadowx=2:shadowy=2"
    )
    subtitle = title.subtitle or ""
    if not subtitle:
        return main
    sub = (
        "drawtext="
        f"{font}text='{escape_drawtext_text(subtitle)}':fontsize=30:fontcolor=white:"
        "x=82:y=h-126:shadowcolor=black:shadowx=2:shadowy=2"
    )
    return f"{main},{sub}"


def discover_font() -> Path | None:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None
