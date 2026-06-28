"""Hero moment on the drop: emphasise the single best beat of the cut.

The clip that lands on the biggest energy peak gets a pronounced "hero" push-in in the renderer, so
the standout moment reads as a deliberate beat instead of just another cut. Beat-safe: it only sets
a flag (the push-in accumulates over the clip without changing its frame count).
"""

from aicutting.core.models import Timeline
from aicutting.director.drone_models import PEAK_ENERGY, BeatPlan


def pick_hero_index(energies: list[float]) -> int | None:
    """The index of the biggest drop -- the highest-energy clip, but only if it is a real peak."""
    if not energies:
        return None
    best = max(range(len(energies)), key=lambda index: energies[index])
    return best if energies[best] >= PEAK_ENERGY else None


def mark_hero(timeline: Timeline, beat_plan: BeatPlan) -> Timeline:
    """Flag the clip on the biggest energy peak as the hero shot (no-op without a clear drop)."""
    energies = [
        _energy_at(beat_plan, clip.timeline_start_s, timeline.target_duration_s)
        for clip in timeline.clips
    ]
    index = pick_hero_index(energies)
    if index is None:
        return timeline
    clips = list(timeline.clips)
    clips[index] = clips[index].model_copy(update={"hero": True})
    return timeline.model_copy(update={"clips": clips})


def _energy_at(beat_plan: BeatPlan, time_s: float, total_s: float) -> float:
    curve = beat_plan.energy_curve
    if not curve or total_s <= 0:
        return 0.0
    ratio = max(0.0, min(1.0, time_s / total_s))
    return float(curve[min(len(curve) - 1, round(ratio * (len(curve) - 1)))])
