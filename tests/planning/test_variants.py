from pathlib import Path

from aicutting.core.models import (
    LocationTitle,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)
from aicutting.planning.variants import LENGTH_VARIANTS, opening_variant


def _timeline(clip_count: int, clip_s: float = 3.0, *, title: bool = True) -> Timeline:
    location = LocationTitle(title="Iceland", subtitle="June 2025", confidence=0.9)
    clips = [
        TimelineClip(
            asset_path=Path(f"clip{i}.mp4"),
            source_start_s=0.0,
            source_end_s=clip_s,
            timeline_start_s=round(i * clip_s, 3),
            transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
            speed=1.0,
            color_intent="subtle_cinematic",
        )
        for i in range(clip_count)
    ]
    return Timeline(
        target_duration_s=round(clip_count * clip_s, 3),
        clips=clips,
        fps=25.0,
        width=1920,
        height=1080,
        grade_strength=1.4,
        title=location if title else None,
    )


def test_opening_variant_keeps_the_first_seconds_of_the_cut() -> None:
    full = _timeline(10)  # 30 s of 3 s clips
    teaser = opening_variant(full, 15.0)
    assert teaser is not None
    # clips starting before 15 s: 0, 3, 6, 9, 12 -> 5 clips, ending at 15 s
    assert len(teaser.clips) == 5
    assert teaser.target_duration_s == 15.0
    assert teaser.clips[0].timeline_start_s == 0.0


def test_opening_variant_preserves_title_grade_and_format() -> None:
    full = _timeline(10)
    teaser = opening_variant(full, 15.0)
    assert teaser is not None
    assert teaser.title == full.title  # the opening keeps the cinematic title reveal
    assert teaser.grade_strength == full.grade_strength
    assert (teaser.width, teaser.height, teaser.fps) == (1920, 1080, 25.0)


def test_opening_variant_is_none_when_the_cut_already_fits() -> None:
    full = _timeline(3)  # 9 s -- already shorter than a 15 s teaser
    assert opening_variant(full, 15.0) is None


def test_opening_variant_is_none_for_a_single_clip() -> None:
    assert opening_variant(_timeline(1), 15.0) is None


def test_length_variants_registry_has_teaser_and_short() -> None:
    names = {variant.name for variant in LENGTH_VARIANTS}
    assert {"teaser", "short"} <= names
    teaser = next(v for v in LENGTH_VARIANTS if v.name == "teaser")
    assert teaser.seconds <= 20.0  # a teaser is short
