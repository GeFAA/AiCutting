"""Build a self-contained HTML run report for the AiCutting drone cutter.

The report reads the JSON artifacts the pipeline writes into ``output_dir`` and
renders a single ``report.html`` that shows what the AI did: the chosen shots and
why, what it rejected, the energy-driven beat grid, and the final timeline with
real thumbnails extracted from the source footage. Every artifact is optional;
the report degrades gracefully to whatever is present.
"""

import html
import json
from collections import Counter
from pathlib import Path
from typing import TypeVar

import cv2
from pydantic import BaseModel, ValidationError

from aicutting.core.models import Timeline, TimelineClip
from aicutting.director.edit_models import (
    Director3Report,
    EditDecision,
    MomentRating,
    RhythmSlot,
)
from aicutting.director.models import LocationSuggestion
from aicutting.quality.critic import EditQuality

ModelT = TypeVar("ModelT", bound=BaseModel)

_THUMB_WIDTH = 320
_BEAT_TOLERANCE_S = 0.18


def build_report(output_dir: Path) -> Path:
    """Read the run artifacts in ``output_dir``, extract thumbnails, write
    ``output_dir/report.html`` and return its path."""
    output_dir = Path(output_dir)
    timeline = _load_model(output_dir / "timeline.json", Timeline)
    ratings = _load_models(output_dir / "footage-ratings.json", MomentRating)
    slots = _load_models(output_dir / "rhythm-grid.json", RhythmSlot)
    edit = _load_model(output_dir / "edit-decision.json", EditDecision)
    director = _load_model(output_dir / "director-3-report.json", Director3Report)
    locations = _load_models(output_dir / "location-suggestions.json", LocationSuggestion)
    quality = _load_model(output_dir / "edit-quality.json", EditQuality)

    clips = list(timeline.clips) if timeline is not None else []
    thumbs = _extract_thumbnails(clips, output_dir / "report-assets")

    document = _render_document(
        timeline, clips, thumbs, ratings, slots, edit, director, locations, quality
    )
    report_path = output_dir / "report.html"
    report_path.write_text(document, encoding="utf-8")
    return report_path


# --------------------------------------------------------------------------- #
# Artifact loading (graceful: never raise on missing or malformed files)
# --------------------------------------------------------------------------- #
def _read_json(path: Path) -> object | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data: object = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data


def _load_model(path: Path, model_type: type[ModelT]) -> ModelT | None:
    payload = _read_json(path)
    if payload is None:
        return None
    try:
        return model_type.model_validate(payload)
    except ValidationError:
        return None


def _load_models(path: Path, model_type: type[ModelT]) -> list[ModelT]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        return []
    models: list[ModelT] = []
    for entry in payload:
        try:
            models.append(model_type.model_validate(entry))
        except ValidationError:
            continue
    return models


# --------------------------------------------------------------------------- #
# Thumbnail extraction
# --------------------------------------------------------------------------- #
def _extract_thumbnails(clips: list[TimelineClip], assets_dir: Path) -> list[str | None]:
    thumbs: list[str | None] = []
    for index, clip in enumerate(clips):
        dest = assets_dir / f"clip-{index:02d}.jpg"
        if _extract_thumbnail(clip, dest):
            thumbs.append(f"report-assets/{dest.name}")
        else:
            thumbs.append(None)
    return thumbs


def _extract_thumbnail(clip: TimelineClip, dest: Path) -> bool:
    capture = cv2.VideoCapture(str(clip.asset_path))
    try:
        if not capture.isOpened():
            return False
        capture.set(cv2.CAP_PROP_POS_MSEC, clip.source_start_s * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            return False
        height, width = frame.shape[:2]
        if width <= 0 or height <= 0:
            return False
        thumb_h = max(1, int(height * (_THUMB_WIDTH / width)))
        thumb = cv2.resize(frame, (_THUMB_WIDTH, thumb_h), interpolation=cv2.INTER_AREA)
        dest.parent.mkdir(parents=True, exist_ok=True)
        return bool(cv2.imwrite(str(dest), thumb))
    finally:
        capture.release()


# --------------------------------------------------------------------------- #
# Small formatting helpers
# --------------------------------------------------------------------------- #
def _esc(value: object) -> str:
    return html.escape(str(value))


def _fmt_seconds(value: float) -> str:
    return f"{value:.1f}s"


def _pct(value: float) -> float:
    return max(0.0, min(1.0, value)) * 100.0


def _slot_for_clip(clip: TimelineClip, slots: list[RhythmSlot]) -> RhythmSlot | None:
    best: RhythmSlot | None = None
    best_delta = _BEAT_TOLERANCE_S
    for slot in slots:
        delta = abs(slot.start_s - clip.timeline_start_s)
        if delta <= best_delta:
            best = slot
            best_delta = delta
    return best


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _render_document(
    timeline: Timeline | None,
    clips: list[TimelineClip],
    thumbs: list[str | None],
    ratings: list[MomentRating],
    slots: list[RhythmSlot],
    edit: EditDecision | None,
    director: Director3Report | None,
    locations: list[LocationSuggestion],
    quality: EditQuality | None,
) -> str:
    body = "\n".join(
        part
        for part in (
            _render_header(timeline, clips, ratings, director, quality),
            _render_warnings(director),
            _render_quality_section(quality),
            _render_cut_section(clips, thumbs, slots, edit),
            _render_selection_section(ratings),
            _render_rhythm_section(slots),
            _render_location_section(locations),
        )
        if part
    )
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>AiCutting &mdash; Run Report</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        f'<body>\n<main class="wrap">\n{body}\n</main>\n</body>\n</html>\n'
    )


def _render_header(
    timeline: Timeline | None,
    clips: list[TimelineClip],
    ratings: list[MomentRating],
    director: Director3Report | None,
    quality: EditQuality | None = None,
) -> str:
    title = "AiCutting Report"
    subtitle = "AI Drone Director"
    if timeline is not None and timeline.title is not None:
        title = timeline.title.title or title
        subtitle = timeline.title.subtitle or subtitle

    rated = director.rated_moments if director is not None else len(ratings)
    kept = director.kept_moments if director is not None else sum(1 for r in ratings if r.keep)
    rejected = max(0, rated - kept)
    backend = director.backend if director is not None and director.backend else "—"
    total = sum(clip.timeline_duration_s for clip in clips)
    fps = f"{timeline.fps:g}" if timeline is not None else "—"
    resolution = f"{timeline.width}×{timeline.height}" if timeline is not None else "—"

    stats = [
        ("Backend", _esc(backend)),
        ("Rated", str(rated)),
        ("Kept", str(kept)),
        ("Rejected", str(rejected)),
        ("Clips", str(len(clips))),
        ("Duration", _fmt_seconds(total)),
        ("FPS", _esc(fps)),
        ("Resolution", _esc(resolution)),
    ]
    if quality is not None:
        stats.append(("Grade", _esc(quality.grade)))
    cards = "\n".join(
        f'<div class="stat"><span class="stat-value">{value}</span>'
        f'<span class="stat-label">{_esc(label)}</span></div>'
        for label, value in stats
    )
    return (
        '<header class="hero">\n'
        f"<h1>{_esc(title)}</h1>\n"
        f'<p class="hero-sub">{_esc(subtitle)}</p>\n'
        f'<div class="stats">\n{cards}\n</div>\n'
        "</header>"
    )


def _render_quality_section(quality: EditQuality | None) -> str:
    # The self-critic: the director's own grade for the finished cut, with a bar per dimension.
    if quality is None or not quality.dimensions:
        return ""
    rows = []
    for dimension in quality.dimensions:
        pct = round(dimension.score * 100)
        label = dimension.name.replace("_", " ").title()
        rows.append(
            '<div class="q-row">\n'
            '<div style="display:flex;justify-content:space-between;margin:14px 0 5px">'
            f"<span>{_esc(label)}</span>"
            f'<span class="bar-num">{pct}%</span></div>\n'
            f'<div class="bar"><div class="bar-fill" style="width:{pct}%"></div></div>\n'
            f'<p class="clip-time" style="margin:5px 0 0">{_esc(dimension.detail)}</p>\n'
            "</div>"
        )
    return (
        '<section class="quality">\n'
        f'<h2>Self-Critic <span class="count">grade {_esc(quality.grade)} '
        f"&middot; {quality.overall:.0%}</span></h2>\n"
        f"{chr(10).join(rows)}\n</section>"
    )


def _render_warnings(director: Director3Report | None) -> str:
    if director is None or not director.warnings:
        return ""
    items = "\n".join(f"<li>{_esc(warning)}</li>" for warning in director.warnings)
    return f'<div class="warnings"><strong>Warnings</strong>\n<ul>{items}</ul></div>'


def _render_cut_section(
    clips: list[TimelineClip],
    thumbs: list[str | None],
    slots: list[RhythmSlot],
    edit: EditDecision | None,
) -> str:
    count = len(clips)
    arc = ""
    if edit is not None and edit.arc:
        arc = f'<p class="arc">Arc: {_esc(edit.arc)}</p>\n'
    if not clips:
        return (
            '<section class="cut">\n'
            f'<h2>The Cut <span class="count">{count} clips</span></h2>\n'
            f"{arc}"
            '<p class="empty">No timeline was found for this run.</p>\n'
            "</section>"
        )
    label = "clip" if count == 1 else "clips"
    cards = "\n".join(
        _render_clip_card(index, clip, thumbs, slots, edit)
        for index, clip in enumerate(clips)
    )
    return (
        '<section class="cut">\n'
        f'<h2>The Cut <span class="count">{count} {label}</span></h2>\n'
        f"{arc}"
        f'<div class="clip-grid">\n{cards}\n</div>\n'
        "</section>"
    )


def _render_clip_card(
    index: int,
    clip: TimelineClip,
    thumbs: list[str | None],
    slots: list[RhythmSlot],
    edit: EditDecision | None,
) -> str:
    thumb_src = thumbs[index] if index < len(thumbs) else None
    badge = f'<span class="thumb-index">#{index + 1}</span>'
    if thumb_src is not None:
        media = (
            '<div class="thumb">'
            f'<img src="{_esc(thumb_src)}" alt="Clip {index + 1} preview" loading="lazy">'
            f"{badge}</div>"
        )
    else:
        media = f'<div class="thumb thumb-empty"><span>no preview</span>{badge}</div>'

    slot = _slot_for_clip(clip, slots)
    if slot is None:
        beat = '<span class="beat beat-off">off beat</span>'
    elif slot.is_accent:
        beat = '<span class="beat beat-accent">on accent</span>'
    else:
        beat = '<span class="beat beat-on">on beat</span>'

    why = ""
    if edit is not None and index < len(edit.clips) and edit.clips[index].reason:
        why = f'<p class="why">{_esc(edit.clips[index].reason)}</p>\n'

    name = _esc(clip.asset_path.name)
    return (
        f'<article class="clip-card" data-clip="{index}">\n'
        f"{media}\n"
        '<div class="clip-body">\n'
        f'<div class="clip-file" title="{name}">{name}</div>\n'
        f'<div class="clip-time">@ {_fmt_seconds(clip.source_start_s)} &middot; '
        f"{_fmt_seconds(clip.timeline_duration_s)}</div>\n"
        '<div class="clip-tags">'
        f'<span class="tag">{_esc(clip.transition_in.kind.value)}</span>{beat}</div>\n'
        f"{why}"
        "</div>\n"
        "</article>"
    )


def _render_selection_section(ratings: list[MomentRating]) -> str:
    if not ratings:
        return (
            '<section class="selection">\n<h2>Selection</h2>\n'
            '<p class="empty">No footage ratings were recorded.</p>\n</section>'
        )
    kept = sum(1 for rating in ratings if rating.keep)
    rejected = len(ratings) - kept
    reason_counts = Counter(rating.reason for rating in ratings if not rating.keep)
    reason_items = "\n".join(
        f'<li><span class="reason-count">{count}×</span> {_esc(reason)}</li>'
        for reason, count in reason_counts.most_common()
    )
    reasons_block = (
        '<div class="reasons"><h3>Why footage was rejected</h3>\n'
        f"<ul>{reason_items}</ul></div>\n"
        if reason_items
        else ""
    )
    rows = "\n".join(_render_rating_row(rating) for rating in ratings)
    return (
        '<section class="selection">\n<h2>Selection</h2>\n'
        '<div class="keepbar">'
        f'<span class="pill pill-keep">{kept} kept</span>'
        f'<span class="pill pill-reject">{rejected} rejected</span></div>\n'
        f"{reasons_block}"
        '<table class="ratings">\n'
        "<thead><tr><th>Moment</th><th>Shot</th><th>Score</th>"
        "<th>Verdict</th><th>Reason</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n</section>"
    )


def _render_rating_row(rating: MomentRating) -> str:
    if rating.keep:
        verdict = '<span class="verdict verdict-keep">keep</span>'
    else:
        verdict = '<span class="verdict verdict-reject">reject</span>'
    return (
        "<tr>"
        f"<td>{_esc(rating.moment_id)}</td>"
        f"<td>{_esc(rating.shot_type.value)}</td>"
        '<td class="score"><div class="bar">'
        f'<div class="bar-fill" style="width:{_pct(rating.cinematic_score):.0f}%"></div></div>'
        f'<span class="bar-num">{rating.cinematic_score:.2f}</span></td>'
        f"<td>{verdict}</td>"
        f"<td>{_esc(rating.reason)}</td>"
        "</tr>"
    )


def _render_rhythm_section(slots: list[RhythmSlot]) -> str:
    if not slots:
        return (
            '<section class="rhythm-section">\n<h2>Rhythm Grid</h2>\n'
            '<p class="empty">No rhythm grid was recorded.</p>\n</section>'
        )
    bars = "\n".join(_render_rhythm_bar(slot) for slot in slots)
    return (
        '<section class="rhythm-section">\n<h2>Rhythm Grid</h2>\n'
        '<p class="muted">Bar height is the slot energy; accents are highlighted.</p>\n'
        f'<div class="rhythm">\n{bars}\n</div>\n</section>'
    )


def _render_rhythm_bar(slot: RhythmSlot) -> str:
    height = max(2.0, _pct(slot.energy))
    css = "rbar rbar-accent" if slot.is_accent else "rbar"
    title = (
        f"slot {slot.index} · {slot.section} · "
        f"energy {slot.energy:.2f} · {_fmt_seconds(slot.start_s)}"
    )
    return f'<div class="{css}" style="height:{height:.0f}%" title="{_esc(title)}"></div>'


def _render_location_section(locations: list[LocationSuggestion]) -> str:
    if not locations:
        return (
            '<section class="location">\n<h2>Location Evidence</h2>\n'
            '<p class="empty">No location suggestions were recorded.</p>\n</section>'
        )
    cards = "\n".join(_render_location_card(location) for location in locations)
    return (
        '<section class="location">\n<h2>Location Evidence</h2>\n'
        f'<div class="loc-grid">\n{cards}\n</div>\n</section>'
    )


def _render_location_card(location: LocationSuggestion) -> str:
    evidence = "\n".join(f"<li>{_esc(item)}</li>" for item in location.evidence)
    evidence_block = f"<ul>{evidence}</ul>\n" if evidence else ""
    if location.should_render:
        render_badge = '<span class="badge badge-on">render</span>'
    else:
        render_badge = '<span class="badge badge-off">skip</span>'
    return (
        '<article class="loc-card">\n'
        f'<div class="loc-head"><h3>{_esc(location.title)}</h3>{render_badge}</div>\n'
        f'<p class="loc-place">{_esc(location.place)}</p>\n'
        f'<div class="conf"><div class="conf-bar" style="width:{_pct(location.confidence):.0f}%">'
        "</div></div>\n"
        f'<p class="conf-num">confidence {location.confidence:.0%}</p>\n'
        f"{evidence_block}"
        "</article>"
    )


_STYLE = """
:root{
  --bg:#0b0d12; --panel:#141821; --panel-2:#1b212d; --line:#262d3a;
  --text:#e8ecf4; --muted:#8a93a6; --accent:#ffb454; --accent-2:#5cc8ff;
  --keep:#39d98a; --reject:#ff6b6b;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--text);
  font-family:"Segoe UI",system-ui,-apple-system,sans-serif; line-height:1.5;
}
.wrap{max-width:1180px; margin:0 auto; padding:32px 24px 64px}
h1{font-size:42px; margin:0; letter-spacing:.5px}
h2{font-size:24px; margin:0 0 16px; display:flex; align-items:baseline; gap:12px}
h3{font-size:16px; margin:0}
section{
  background:var(--panel); border:1px solid var(--line);
  border-radius:14px; padding:24px; margin-top:24px;
}
.hero{
  background:linear-gradient(160deg,#1a2030,#0c0f16);
  border:1px solid var(--line); border-radius:16px; padding:32px;
}
.hero-sub{
  color:var(--accent); margin:6px 0 22px; font-size:14px;
  letter-spacing:2px; text-transform:uppercase;
}
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(108px,1fr)); gap:12px}
.stat{
  background:var(--panel-2); border:1px solid var(--line);
  border-radius:10px; padding:12px 14px;
}
.stat-value{display:block; font-size:22px; font-weight:700}
.stat-label{
  display:block; color:var(--muted); font-size:11px;
  text-transform:uppercase; letter-spacing:1px; margin-top:2px;
}
.count{font-size:13px; color:var(--muted); font-weight:500}
.arc{color:var(--accent-2); margin:-6px 0 18px; font-style:italic}
.clip-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px}
.clip-card{
  background:var(--panel-2); border:1px solid var(--line);
  border-radius:12px; overflow:hidden;
}
.thumb{
  position:relative; aspect-ratio:16/9; background:#000;
  display:flex; align-items:center; justify-content:center;
}
.thumb img{width:100%; height:100%; object-fit:cover; display:block}
.thumb-empty{color:var(--muted); font-size:13px}
.thumb-index{
  position:absolute; top:8px; left:8px; background:rgba(0,0,0,.65);
  padding:2px 8px; border-radius:20px; font-size:12px; font-weight:600;
}
.clip-body{padding:12px 14px}
.clip-file{
  font-weight:600; font-size:14px; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap;
}
.clip-time{color:var(--muted); font-size:12px; margin:3px 0 10px}
.clip-tags{display:flex; gap:6px; flex-wrap:wrap}
.tag,.beat,.pill,.badge{
  font-size:11px; padding:3px 9px; border-radius:20px; font-weight:600;
}
.tag{background:#23304a; color:var(--accent-2)}
.beat-on{background:#1d3b2c; color:var(--keep)}
.beat-accent{background:#3a2a12; color:var(--accent)}
.beat-off{background:#2a2f3a; color:var(--muted)}
.why{
  color:var(--muted); font-size:12px; margin:10px 0 0;
  border-left:2px solid var(--line); padding-left:8px;
}
.keepbar{display:flex; gap:10px; margin-bottom:16px}
.pill-keep{background:#173e2c; color:var(--keep)}
.pill-reject{background:#3e1d1d; color:var(--reject)}
.reasons{margin-bottom:18px}
.reasons ul{margin:8px 0 0; padding-left:18px}
.reasons li{margin:4px 0}
.reason-count{color:var(--accent); font-weight:700; margin-right:4px}
table.ratings{width:100%; border-collapse:collapse; font-size:13px}
.ratings th,.ratings td{text-align:left; padding:8px 10px; border-bottom:1px solid var(--line)}
.ratings th{
  color:var(--muted); font-weight:600; text-transform:uppercase;
  font-size:11px; letter-spacing:1px;
}
.score{display:flex; align-items:center; gap:8px; min-width:140px}
.bar{flex:1; height:8px; background:#222a38; border-radius:6px; overflow:hidden}
.bar-fill{height:100%; background:linear-gradient(90deg,var(--accent-2),var(--accent))}
.bar-num{color:var(--muted); font-variant-numeric:tabular-nums}
.verdict-keep{color:var(--keep)}
.verdict-reject{color:var(--reject)}
.rhythm{display:flex; align-items:flex-end; gap:4px; height:150px; padding-top:10px}
.rbar{
  flex:1; min-height:2px; border-radius:4px 4px 0 0;
  background:linear-gradient(180deg,var(--accent-2),#2a4a66);
}
.rbar-accent{background:linear-gradient(180deg,var(--accent),#7a4d12)}
.loc-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px}
.loc-card{
  background:var(--panel-2); border:1px solid var(--line);
  border-radius:12px; padding:16px;
}
.loc-head{display:flex; justify-content:space-between; align-items:center; gap:10px}
.loc-place{color:var(--muted); margin:4px 0 12px}
.badge-on{background:#173e2c; color:var(--keep)}
.badge-off{background:#2a2f3a; color:var(--muted)}
.conf{height:6px; background:#222a38; border-radius:6px; overflow:hidden}
.conf-bar{height:100%; background:linear-gradient(90deg,var(--accent-2),var(--accent))}
.conf-num{color:var(--muted); font-size:12px; margin:6px 0 12px}
.loc-card ul{margin:0; padding-left:18px}
.loc-card li{margin:4px 0; font-size:13px}
.warnings{
  background:#3a2a12; border:1px solid #5a431d; border-radius:12px;
  padding:14px 18px; margin-top:24px; color:var(--accent);
}
.warnings ul{margin:8px 0 0}
.muted,.empty{color:var(--muted)}
.empty{font-style:italic}
"""
