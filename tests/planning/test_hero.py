from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.director.drone_models import BeatPlan, BeatSection
from aicutting.planning.hero import mark_hero, pick_hero_index


def test_pick_hero_index_is_the_biggest_peak() -> None:
    assert pick_hero_index([0.2, 0.9, 0.5, 0.85]) == 1  # the highest, and it's a real peak


def test_pick_hero_index_none_without_a_real_drop() -> None:
    # nothing reaches a peak -> no hero (don't crown a calm shot)
    assert pick_hero_index([0.2, 0.3, 0.5]) is None
    assert pick_hero_index([]) is None


def _clip(timeline_start: float) -> TimelineClip:
    return TimelineClip(
        asset_path=Path("a.mp4"),
        source_start_s=0.0,
        source_end_s=2.0,
        timeline_start_s=timeline_start,
        transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
        speed=1.0,
        color_intent="subtle_cinematic",
    )


def test_mark_hero_flags_the_clip_on_the_energy_peak() -> None:
    clips = [_clip(0.0), _clip(2.0), _clip(4.0)]
    timeline = Timeline(target_duration_s=6.0, clips=clips, fps=25.0, width=1920, height=1080)
    # energy curve rising to a peak in the middle third (where clip 1 lands)
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0, 4.0],
        energy_curve=[0.2, 0.95, 0.3],
        sections=[BeatSection(label="peak", start_s=0.0, end_s=6.0, energy=0.5, cut_density=0.5)],
    )

    marked = mark_hero(timeline, beat_plan)

    assert [clip.hero for clip in marked.clips] == [False, True, False]


def test_mark_hero_leaves_a_calm_cut_untouched() -> None:
    clips = [_clip(0.0), _clip(2.0)]
    timeline = Timeline(target_duration_s=4.0, clips=clips, fps=25.0, width=1920, height=1080)
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0],
        energy_curve=[0.2, 0.3],  # never reaches a peak
        sections=[BeatSection(label="calm", start_s=0.0, end_s=4.0, energy=0.25, cut_density=0.3)],
    )

    marked = mark_hero(timeline, beat_plan)

    assert all(not clip.hero for clip in marked.clips)
