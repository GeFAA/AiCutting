from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.quality.critic import EditQuality, score_edit


def _clip(
    asset: str,
    source_start: float,
    source_end: float,
    timeline_start: float,
    kind: TransitionType = TransitionType.HARD_CUT,
    duration: float = 0.0,
    speed: float = 1.0,
) -> TimelineClip:
    return TimelineClip(
        asset_path=Path(asset),
        source_start_s=source_start,
        source_end_s=source_end,
        timeline_start_s=timeline_start,
        transition_in=Transition(kind=kind, duration_s=duration),
        speed=speed,
        color_intent="subtle_cinematic",
    )


def _timeline(clips: list[TimelineClip]) -> Timeline:
    span = max(clip.timeline_start_s for clip in clips) + 2.0
    return Timeline(target_duration_s=span, clips=clips, fps=25.0, width=1920, height=1080)


def _dimension(quality: EditQuality, name: str) -> float:
    return next(dimension.score for dimension in quality.dimensions if dimension.name == name)


def test_cuts_that_land_on_beats_score_high() -> None:
    beats = [float(i) for i in range(0, 16, 2)]  # 0, 2, 4, ...
    clips = [
        _clip("a.mp4", 0, 2, 0.0),
        _clip("b.mp4", 10, 12, 2.0),  # cut on beat 2
        _clip("c.mp4", 20, 22, 4.0),  # cut on beat 4
        _clip("d.mp4", 30, 32, 6.0),  # cut on beat 6
    ]
    quality = score_edit(_timeline(clips), beats)
    assert _dimension(quality, "on_beat") >= 0.95


def test_cuts_midway_between_beats_score_low() -> None:
    beats = [float(i) for i in range(0, 16, 2)]
    clips = [
        _clip("a.mp4", 0, 2, 0.0),
        _clip("b.mp4", 10, 12, 1.0),  # cut at 1.0 -- exactly between beats 0 and 2
        _clip("c.mp4", 20, 22, 3.0),  # cut at 3.0 -- between beats 2 and 4
    ]
    quality = score_edit(_timeline(clips), beats)
    assert _dimension(quality, "on_beat") <= 0.2


def test_adjacent_duplicate_sources_penalise_variety() -> None:
    beats = [float(i) for i in range(0, 16, 2)]
    repeated = [_clip("a.mp4", 10, 12, float(i * 2)) for i in range(4)]  # same source four times
    distinct = [_clip(f"{c}.mp4", 10, 12, float(i * 2)) for i, c in enumerate("abcd")]

    repeated_variety = _dimension(score_edit(_timeline(repeated), beats), "variety")
    distinct_variety = _dimension(score_edit(_timeline(distinct), beats), "variety")

    assert distinct_variety > repeated_variety
    assert repeated_variety < 0.5


def test_monotonous_pacing_scores_below_varied_pacing() -> None:
    beats = [float(i) for i in range(0, 40, 2)]
    flat = [_clip(f"{i}.mp4", 0, 2, float(i * 2)) for i in range(6)]  # every clip 2.0 s
    varied = [
        _clip("a.mp4", 0, 2, 0.0),
        _clip("b.mp4", 0, 4, 2.0),
        _clip("c.mp4", 0, 2, 6.0),
        _clip("d.mp4", 0, 6, 8.0),
        _clip("e.mp4", 0, 2, 14.0),
        _clip("f.mp4", 0, 4, 16.0),
    ]
    assert _dimension(score_edit(_timeline(varied), beats), "pacing") > _dimension(
        score_edit(_timeline(flat), beats), "pacing"
    )


def test_a_clean_cut_earns_an_a_grade() -> None:
    beats = [float(i) for i in range(0, 40, 2)]
    clips = [
        _clip("a.mp4", 0, 2, 0.0),
        _clip("b.mp4", 0, 4, 2.0),
        _clip("c.mp4", 0, 2, 6.0),
        _clip("d.mp4", 0, 6, 8.0),
        _clip("e.mp4", 0, 2, 14.0),
        _clip("f.mp4", 0, 4, 16.0),
    ]
    quality = score_edit(_timeline(clips), beats)
    assert isinstance(quality, EditQuality)
    assert quality.overall >= 0.9
    assert quality.grade == "A"


def test_a_sloppy_cut_earns_a_failing_grade() -> None:
    beats = [float(i) for i in range(0, 16, 2)]
    # off-beat cuts AND the same source repeated AND flat pacing -> weak on every dimension.
    clips = [_clip("a.mp4", 10, 12, i + 0.9) for i in range(4)]
    quality = score_edit(_timeline(clips), beats)
    assert quality.overall < 0.6
    assert quality.grade in {"D", "F"}


def test_missing_beats_omit_the_on_beat_dimension() -> None:
    clips = [_clip("a.mp4", 0, 2, 0.0), _clip("b.mp4", 0, 2, 2.0)]
    quality = score_edit(_timeline(clips), [])
    assert all(dimension.name != "on_beat" for dimension in quality.dimensions)
    assert 0.0 <= quality.overall <= 1.0
