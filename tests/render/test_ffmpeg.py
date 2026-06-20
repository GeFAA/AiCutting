import subprocess
from pathlib import Path

import pytest

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import Timeline, TimelineClip, Transition, TransitionType
from aicutting.render.ffmpeg import build_ffmpeg_command, render_timeline


def _timeline() -> Timeline:
    return Timeline(
        target_duration_s=4.0,
        fps=25.0,
        width=1920,
        height=1080,
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


def test_build_ffmpeg_command_contains_trim_and_output() -> None:
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)

    assert command[0] == "ffmpeg"
    assert "clip.mp4" in command
    assert "out/final.mp4" in command
    assert any("trim=start=1.0:end=5.0" in part for part in command)


def test_render_timeline_wraps_missing_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ExternalToolError, match="FFmpeg is not available"):
        render_timeline(_timeline(), tmp_path / "final.mp4", music_path=None)
