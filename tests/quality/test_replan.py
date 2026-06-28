from pathlib import Path

from aicutting.core.models import CutPlan, Timeline, TimelineClip, Transition, TransitionType
from aicutting.quality.critic import better_graded_plan, replan_if_weak


def _clip(asset: str, timeline_start: float) -> TimelineClip:
    return TimelineClip(
        asset_path=Path(asset),
        source_start_s=0.0,
        source_end_s=2.0,
        timeline_start_s=timeline_start,
        transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
        speed=1.0,
        color_intent="subtle_cinematic",
    )


def _plan(clips: list[TimelineClip]) -> CutPlan:
    timeline = Timeline(target_duration_s=8.0, clips=clips, fps=25.0, width=1920, height=1080)
    return CutPlan(target_duration_s=8.0, style="x", timeline=timeline, notes=[])


def test_keeps_the_higher_graded_cut() -> None:
    beats = [0.0, 2.0, 4.0, 6.0]
    on_beat = _plan([_clip("a.mp4", 0.0), _clip("b.mp4", 2.0), _clip("c.mp4", 4.0)])  # on beats
    off_beat = _plan([_clip("a.mp4", 0.0), _clip("b.mp4", 1.0), _clip("c.mp4", 3.0)])  # off beats

    assert better_graded_plan(off_beat, on_beat, beats) is on_beat
    assert better_graded_plan(on_beat, off_beat, beats) is on_beat


def test_prefers_the_primary_on_a_tie() -> None:
    beats = [0.0, 2.0, 4.0]
    primary = _plan([_clip("a.mp4", 0.0), _clip("b.mp4", 2.0)])
    alternative = _plan([_clip("c.mp4", 0.0), _clip("d.mp4", 2.0)])  # same grade

    assert better_graded_plan(primary, alternative, beats) is primary


def _weak_plan() -> CutPlan:
    # off-beat cuts, one repeated source, flat pacing -> weak on every dimension
    return _plan([_clip("a.mp4", 0.9), _clip("a.mp4", 1.9), _clip("a.mp4", 2.9)])


def test_replan_keeps_a_strong_primary_without_building_an_alternative() -> None:
    beats = [0.0, 2.0, 4.0, 6.0]
    strong = _plan([_clip("a.mp4", 0.0), _clip("b.mp4", 2.0), _clip("c.mp4", 4.0)])
    built = False

    def build_alternative() -> CutPlan:
        nonlocal built
        built = True
        return _plan([_clip("d.mp4", 0.0)])

    result = replan_if_weak(strong, beats, build_alternative)

    assert result is strong
    assert built is False  # a strong cut never pays to build the alternative


def test_replan_swaps_a_weak_primary_for_a_better_alternative() -> None:
    beats = [0.0, 2.0, 4.0, 6.0]
    weak = _weak_plan()
    better = _plan([_clip("a.mp4", 0.0), _clip("b.mp4", 2.0), _clip("c.mp4", 4.0)])

    assert replan_if_weak(weak, beats, lambda: better) is better


def test_replan_keeps_the_weak_primary_when_the_alternative_is_no_better() -> None:
    beats = [0.0, 2.0, 4.0, 6.0]
    weak = _weak_plan()

    assert replan_if_weak(weak, beats, _weak_plan) is weak  # tie -> keep the primary
