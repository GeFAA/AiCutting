import subprocess
from pathlib import Path

import pytest

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import LocationTitle, Timeline, TimelineClip, Transition, TransitionType
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


def test_build_ffmpeg_command_seeks_each_clip_input_and_outputs_video() -> None:
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)

    assert command[0] == "ffmpeg"
    assert "clip.mp4" in command
    assert "out/final.mp4" in command
    input_index = command.index("clip.mp4")
    assert command[input_index - 5 : input_index] == ["-ss", "1.0", "-t", "4.0", "-i"]
    assert not any("trim=start=1.0:end=5.0" in part for part in command)


def test_build_ffmpeg_command_renders_dissolve_transitions() -> None:
    timeline = Timeline(
        target_duration_s=8.0,
        fps=25.0,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("a.mp4"),
                source_start_s=1.0,
                source_end_s=5.0,
                timeline_start_s=0.0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
                speed=1.0,
                color_intent="subtle_cinematic",
            ),
            TimelineClip(
                asset_path=Path("b.mp4"),
                source_start_s=2.0,
                source_end_s=6.0,
                timeline_start_s=4.0,
                transition_in=Transition(kind=TransitionType.DISSOLVE, duration_s=0.35),
                speed=1.0,
                color_intent="subtle_cinematic",
            ),
        ],
    )

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "xfade=transition=fade:duration=0.35:offset=3.65" in filter_complex
    assert "concat=" not in filter_complex


def test_build_ffmpeg_command_mixes_hard_cuts_and_dissolves() -> None:
    timeline = Timeline(
        target_duration_s=12.0,
        fps=25.0,
        width=1920,
        height=1080,
        clips=[
            TimelineClip(
                asset_path=Path("a.mp4"),
                source_start_s=1.0,
                source_end_s=5.0,
                timeline_start_s=0.0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
                speed=1.0,
                color_intent="subtle_cinematic",
            ),
            TimelineClip(
                asset_path=Path("b.mp4"),
                source_start_s=2.0,
                source_end_s=6.0,
                timeline_start_s=4.0,
                transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
                speed=1.0,
                color_intent="subtle_cinematic",
            ),
            TimelineClip(
                asset_path=Path("c.mp4"),
                source_start_s=3.0,
                source_end_s=7.0,
                timeline_start_s=8.0,
                transition_in=Transition(kind=TransitionType.DISSOLVE, duration_s=0.35),
                speed=1.0,
                color_intent="subtle_cinematic",
            ),
        ],
    )

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "[v0][v1]concat=n=2:v=1:a=0[x1]" in filter_complex
    assert "[x1][v2]xfade=transition=fade:duration=0.35:offset=7.65[vout]" in filter_complex


def test_build_ffmpeg_command_adds_title_overlay_when_present() -> None:
    timeline = _timeline()
    timeline = timeline.model_copy(
        update={"title": LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.9)}
    )
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "drawtext=" in filter_complex


def test_render_timeline_wraps_missing_ffmpeg(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ExternalToolError, match="FFmpeg is not available"):
        render_timeline(_timeline(), tmp_path / "final.mp4", music_path=None)


def test_render_timeline_decodes_ffmpeg_output_losslessly_enough(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["errors"] == "replace"
        return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="bad \ufffd")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ExternalToolError, match="bad"):
        render_timeline(_timeline(), tmp_path / "final.mp4", music_path=None)
