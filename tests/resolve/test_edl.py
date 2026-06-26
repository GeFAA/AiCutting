from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.resolve.edl import timeline_to_edl


def test_timeline_to_edl_contains_title_and_clip_name() -> None:
    timeline = Timeline(
        target_duration_s=4,
        fps=25,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=0,
                source_end_s=4,
                timeline_start_s=0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0),
                speed=1,
                color_intent="subtle_cinematic",
            )
        ],
    )

    edl = timeline_to_edl(timeline)

    assert "TITLE: AiCutting" in edl
    assert "* FROM CLIP NAME: clip.mp4" in edl


def test_timeline_to_edl_uses_clip_timecodes() -> None:
    timeline = Timeline(
        target_duration_s=2,
        fps=25,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("clip.mp4"),
                source_start_s=1,
                source_end_s=3,
                timeline_start_s=5,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0),
                speed=1,
                color_intent="subtle_cinematic",
            )
        ],
    )

    edl = timeline_to_edl(timeline)

    assert "00:00:01:00 00:00:03:00 00:00:05:00 00:00:07:00" in edl
