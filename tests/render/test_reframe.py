from pathlib import Path

from aicutting.core.models import (
    LocationTitle,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)
from aicutting.render.reframe import reframe_timeline, resolve_aspect


def _timeline() -> Timeline:
    # A 4K landscape master with a grade and a title -- everything a reframe must carry across.
    return Timeline(
        target_duration_s=4.0,
        fps=25.0,
        width=3840,
        height=2160,
        grade_strength=1.4,
        title=LocationTitle(title="Reykjavik", subtitle="June 2025", confidence=0.9),
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=1.0,
                source_end_s=5.0,
                timeline_start_s=0.0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
                speed=1.0,
                color_intent="subtle_cinematic",
            )
        ],
    )


def test_reframe_to_vertical_sets_a_1080x1920_master() -> None:
    vertical = reframe_timeline(_timeline(), "9:16")
    assert (vertical.width, vertical.height) == (1080, 1920)


def test_reframe_to_square_sets_a_1080x1080_master() -> None:
    square = reframe_timeline(_timeline(), "1:1")
    assert (square.width, square.height) == (1080, 1080)


def test_reframe_preserves_the_cut_clips_fps_grade_and_title() -> None:
    original = _timeline()
    vertical = reframe_timeline(original, "9:16")
    # Only the frame size changes -- the cut itself is untouched.
    assert vertical.clips == original.clips
    assert vertical.fps == original.fps
    assert vertical.grade_strength == original.grade_strength
    assert vertical.title == original.title
    assert vertical.target_duration_s == original.target_duration_s


def test_reframe_to_landscape_keeps_the_source_master_untouched() -> None:
    original = _timeline()
    same = reframe_timeline(original, "16:9")
    assert (same.width, same.height) == (3840, 2160)


def test_reframe_unknown_aspect_keeps_the_source_master() -> None:
    original = _timeline()
    same = reframe_timeline(original, "banana")
    assert (same.width, same.height) == (original.width, original.height)


def test_resolve_aspect_normalises_known_values() -> None:
    assert resolve_aspect("9:16") == "9:16"
    assert resolve_aspect(" 16:9 ") == "16:9"
    assert resolve_aspect("1:1") == "1:1"


def test_resolve_aspect_unknown_falls_back_to_landscape() -> None:
    assert resolve_aspect("4:3") == "16:9"
    assert resolve_aspect("nonsense") == "16:9"


def test_resolve_aspect_strips_internal_spaces() -> None:
    assert resolve_aspect("9 : 16") == "9:16"
