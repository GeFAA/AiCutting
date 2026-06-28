"""Resolve what to show in the live working view from the artifacts the pipeline has written.

Pure and best-effort: given the current phase and the output folder, return the hero image, the
thumbnail strip, and a one-line detail. The pipeline already writes these artifacts as it runs, so
the GUI just reads them on each progress event -- no pipeline change.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from aicutting.core.progress import PipelinePhase

_WATCH = {
    PipelinePhase.ANALYZING_FOOTAGE,
    PipelinePhase.ANALYZING_MUSIC,
    PipelinePhase.IDENTIFYING_LOCATION,
}
_DIRECT = {PipelinePhase.RATING_FOOTAGE, PipelinePhase.DESIGNING_EDIT}
_CUT = {
    PipelinePhase.ASSEMBLING_CUT,
    PipelinePhase.PLANNING_CUT,
    PipelinePhase.BUILDING_REPORT,
    PipelinePhase.EXPORTING_RESOLVE_HANDOFF,
    PipelinePhase.RENDERING_FINAL_VIDEO,
    PipelinePhase.DONE,
}


@dataclass(frozen=True)
class LiveView:
    hero: str = ""
    thumbnails: list[str] = field(default_factory=list)
    detail: str = ""


def live_view(phase: PipelinePhase, output_dir: Path) -> LiveView:
    out = Path(output_dir)
    if phase in _DIRECT:
        return LiveView(thumbnails=_images(out / "contact-sheets")[:8], detail=_rating_detail(out))
    if phase in _CUT:
        thumbs = _images(out / "report-assets") or _images(out / "contact-sheets")
        return LiveView(thumbnails=thumbs[:8], detail=_rating_detail(out))
    if phase in _WATCH:
        shots = _images(out / "location-screenshots")
        return LiveView(hero=shots[0] if shots else "", detail=_location_detail(out))
    return LiveView()


def _images(folder: Path) -> list[str]:
    try:
        return sorted(str(p) for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".png"})
    except OSError:
        return []


def _location_detail(out: Path) -> str:
    try:
        data = json.loads((out / "location-suggestions.json").read_text(encoding="utf-8"))
        best = max(data, key=lambda d: d.get("confidence", 0.0), default=None)
        if best and best.get("should_render"):
            place = best.get("title") or best.get("place") or "?"
            return f"{place} ({best.get('confidence', 0.0):.2f})"
    except Exception:
        pass
    return ""


def _rating_detail(out: Path) -> str:
    try:
        ratings = json.loads((out / "footage-ratings.json").read_text(encoding="utf-8"))
        if isinstance(ratings, list) and ratings:
            kept = sum(1 for r in ratings if r.get("keep"))
            return f"kept {kept} · rejected {len(ratings) - kept}"
    except Exception:
        pass
    return ""
