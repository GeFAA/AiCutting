from pathlib import Path

from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.resolve.export import export_resolve_handoff


def test_export_resolve_handoff_writes_artifacts(tmp_path: Path) -> None:
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

    export_resolve_handoff(timeline, tmp_path)

    assert (tmp_path / "resolve" / "timeline.fcpxml").exists()
    assert (tmp_path / "resolve" / "timeline.edl").exists()
    assert (tmp_path / "resolve" / "media-manifest.txt").read_text(
        encoding="utf-8"
    ).strip() == "clip.mp4"
