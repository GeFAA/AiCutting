import statistics
from collections.abc import Callable

from pydantic import BaseModel, Field

from aicutting.core.models import CutPlan, Timeline, TimelineClip

# How far a cut may sit from a beat before it stops counting as "on the beat". 0.12 s is ~3 frames
# at 25 fps -- our cuts are laid on absolute beat times, so an honest edit scores ~1.0 here.
_ON_BEAT_TOLERANCE_S = 0.12
# Pacing variation (coefficient of variation of clip lengths) that already reads as dynamic; at or
# above this the pacing score saturates, so an edit is not pushed toward ever-wilder length swings.
_PACING_TARGET_CV = 0.3

# Weights for the overall score. On-beat is the core promise of the tool, so it carries the most.
_WEIGHTS = {"on_beat": 0.5, "variety": 0.3, "pacing": 0.2}

# Below this grade a cut is weak enough to be worth re-planning (0.7 == a C; A/B cuts ship as-is).
REPLAN_THRESHOLD = 0.7


class DimensionScore(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    detail: str


class EditQuality(BaseModel):
    overall: float = Field(ge=0, le=1)
    grade: str
    dimensions: list[DimensionScore]


def score_edit(timeline: Timeline, beats_s: list[float]) -> EditQuality:
    """Grade a finished cut on the dimensions a human editor would eyeball.

    Read-only: it never alters the timeline. ``on_beat`` is reported only when beats are known and
    there is at least one cut to score; ``variety`` and ``pacing`` always apply. The overall score
    is the weighted mean of whichever dimensions were measured, mapped to an A-F grade.
    """
    clips = timeline.clips
    dimensions: list[DimensionScore] = []

    on_beat = _score_on_beat(clips, beats_s)
    if on_beat is not None:
        dimensions.append(on_beat)
    dimensions.append(_score_variety(clips))
    dimensions.append(_score_pacing(clips))

    weighted = sum(_WEIGHTS[d.name] * d.score for d in dimensions)
    total_weight = sum(_WEIGHTS[d.name] for d in dimensions)
    overall = round(weighted / total_weight, 4) if total_weight else 0.0
    return EditQuality(overall=overall, grade=_grade(overall), dimensions=dimensions)


def better_graded_plan(primary: CutPlan, alternative: CutPlan, beats_s: list[float]) -> CutPlan:
    """Return whichever cut the self-critic grades higher (the primary wins a tie)."""
    primary_score = score_edit(primary.timeline, beats_s).overall
    alternative_score = score_edit(alternative.timeline, beats_s).overall
    return alternative if alternative_score > primary_score else primary


def replan_if_weak(
    primary: CutPlan,
    beats_s: list[float],
    build_alternative: Callable[[], CutPlan],
    threshold: float = REPLAN_THRESHOLD,
) -> CutPlan:
    """Close the re-plan loop: if ``primary`` grades at/above ``threshold`` keep it (the alternative
    is never built); otherwise assemble the alternative and keep whichever the critic grades higher.
    """
    if score_edit(primary.timeline, beats_s).overall >= threshold:
        return primary
    return better_graded_plan(primary, build_alternative(), beats_s)


def _score_on_beat(clips: list[TimelineClip], beats_s: list[float]) -> DimensionScore | None:
    cuts = [clip.timeline_start_s for clip in clips[1:]]  # clip 0 is the chain base, not a cut
    if not beats_s or not cuts:
        return None
    drifts = [min(abs(cut - beat) for beat in beats_s) for cut in cuts]
    per_cut = [max(0.0, 1.0 - drift / _ON_BEAT_TOLERANCE_S) for drift in drifts]
    score = sum(per_cut) / len(per_cut)
    mean_drift_ms = (sum(drifts) / len(drifts)) * 1000
    on_count = sum(1 for drift in drifts if drift <= _ON_BEAT_TOLERANCE_S)
    return DimensionScore(
        name="on_beat",
        score=round(score, 4),
        detail=f"{on_count}/{len(cuts)} cuts on the beat (mean drift {mean_drift_ms:.0f} ms)",
    )


def _score_variety(clips: list[TimelineClip]) -> DimensionScore:
    if not clips:
        return DimensionScore(name="variety", score=0.0, detail="no clips")
    keys = [(str(clip.asset_path), round(clip.source_start_s, 1)) for clip in clips]
    distinct = len(set(keys))
    base = distinct / len(keys)
    adjacent_repeats = sum(1 for a, b in zip(keys, keys[1:], strict=False) if a == b)
    penalty = adjacent_repeats / max(1, len(keys) - 1)
    score = max(0.0, min(1.0, base - penalty))
    return DimensionScore(
        name="variety",
        score=round(score, 4),
        detail=f"{distinct} distinct shots across {len(keys)} clips, "
        f"{adjacent_repeats} back-to-back repeat(s)",
    )


def _score_pacing(clips: list[TimelineClip]) -> DimensionScore:
    durations = [clip.timeline_duration_s for clip in clips]
    if len(durations) < 2:
        return DimensionScore(name="pacing", score=1.0, detail="single clip")
    mean = statistics.fmean(durations)
    cv = statistics.pstdev(durations) / mean if mean > 0 else 0.0
    score = max(0.0, min(1.0, cv / _PACING_TARGET_CV))
    return DimensionScore(
        name="pacing",
        score=round(score, 4),
        detail=f"clip length {min(durations):.1f}-{max(durations):.1f}s (variation {cv:.2f})",
    )


def _grade(overall: float) -> str:
    for threshold, letter in ((0.9, "A"), (0.8, "B"), (0.7, "C"), (0.6, "D")):
        if overall >= threshold:
            return letter
    return "F"
