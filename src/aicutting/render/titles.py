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
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_drawtext_filter(title: LocationTitle, font_path: Path | None) -> str:
    font = f":fontfile='{font_path.as_posix()}'" if font_path else ""
    title_text = escape_drawtext_text(title.title)
    subtitle = escape_drawtext_text(title.subtitle or "")
    main = (
        "drawtext="
        f"text='{title_text}'{font}:fontsize=54:fontcolor=white:"
        "x=80:y=h-190:shadowcolor=black:shadowx=2:shadowy=2"
    )
    if not subtitle:
        return main
    sub = (
        "drawtext="
        f"text='{subtitle}'{font}:fontsize=30:fontcolor=white:"
        "x=82:y=h-126:shadowcolor=black:shadowx=2:shadowy=2"
    )
    return f"{main},{sub}"


def discover_font() -> Path | None:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    return None
