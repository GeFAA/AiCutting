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


def test_clips_get_a_cinematic_colour_grade() -> None:
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "eq=contrast=" in filter_complex
    assert "colorbalance=" in filter_complex


def test_landscape_master_scales_straight_to_frame_without_cropping() -> None:
    # The shipped 16:9 master scales straight to the frame -- no cover-crop, byte-identical.
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "scale=1920:1080," in filter_complex
    assert "force_original_aspect_ratio" not in filter_complex
    assert "crop=" not in filter_complex


def test_vertical_master_cover_crops_each_clip() -> None:
    # A 9:16 master covers the frame and centre-crops, so a landscape source fills the vertical
    # frame with no stretched pixels and no letterbox bars.
    vertical = _timeline().model_copy(update={"width": 1080, "height": 1920})
    command = build_ffmpeg_command(vertical, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" in filter_complex
    # never the plain stretch-to-frame that would distort a 16:9 source
    assert "scale=1080:1920," not in filter_complex


def test_content_aware_crop_offsets_the_window() -> None:
    vertical = _timeline().model_copy(update={"width": 1080, "height": 1920})
    biased = vertical.clips[0].model_copy(update={"crop_x": 0.0})  # subject hard-left
    timeline = vertical.model_copy(update={"clips": [biased]})
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "crop=1080:1920:x=(iw-1080)*0:y=" in filter_complex


def test_centred_crop_x_keeps_the_plain_cover_crop() -> None:
    # the default crop_x (0.5) adds no x/y offset -> byte-identical to the shipped cover-crop
    vertical = _timeline().model_copy(update={"width": 1080, "height": 1920})
    command = build_ffmpeg_command(vertical, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "crop=1080:1920:x=" not in filter_complex


def test_color_matched_clip_gets_a_channel_mixer() -> None:
    base = _timeline()
    matched = base.clips[0].model_copy(update={"color_gain": (1.1, 1.0, 0.92)})
    timeline = base.model_copy(update={"clips": [matched]})
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "colorchannelmixer=rr=1.1:gg=1:bb=0.92" in filter_complex


def test_unit_color_gain_adds_no_channel_mixer() -> None:
    # The default (1.0, 1.0, 1.0) gain is a no-op -> byte-identical to the ungraded-match path.
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "colorchannelmixer" not in filter_complex


def test_levelled_clip_rotates_in_source_space_with_overscan() -> None:
    base = _timeline()
    tilted = base.clips[0].model_copy(update={"level_deg": -3.0})
    timeline = base.model_copy(update={"clips": [tilted]})
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "rotate=" in filter_complex
    assert "crop=iw/" in filter_complex  # the same-aspect overscan crop that hides the corners
    # the rotation happens in source space, before the frame scale
    assert filter_complex.index("rotate=") < filter_complex.index("scale=1920:1080")


def test_zero_level_adds_no_rotation() -> None:
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "rotate=" not in filter_complex


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
    assert "Madeira Coast" in filter_complex
    # The cinematic reveal is spliced onto [vbase]: a luma-masked, composited [vout].
    assert "[vbase]format=yuv420p,split=2[base][src]" in filter_complex
    assert "blend=all_expr=" in filter_complex
    assert "overlay=eof_action=pass[vout]" in filter_complex


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


def test_build_ffmpeg_command_renders_smooth_zoom_as_filter() -> None:
    base = _timeline()
    second = base.clips[0].model_copy(
        update={
            "asset_path": Path("clip-b.mp4"),
            "timeline_start_s": 4.0,
            "transition_in": Transition(kind=TransitionType.SMOOTH_ZOOM, duration_s=0.25),
        }
    )
    timeline = base.model_copy(update={"clips": [base.clips[0], second]})

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "zoompan" in filter_complex or "xfade" in filter_complex


def test_smooth_zoom_clip_gets_zoompan_animation() -> None:
    base = _timeline()
    second = base.clips[0].model_copy(
        update={
            "asset_path": Path("clip-b.mp4"),
            "timeline_start_s": 4.0,
            "transition_in": Transition(kind=TransitionType.SMOOTH_ZOOM, duration_s=0.25),
        }
    )
    timeline = base.model_copy(update={"clips": [base.clips[0], second]})

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "zoompan" in filter_complex
    assert "xfade=transition=fade" in filter_complex  # gentle crossfade + push-in


def test_smooth_zoom_fps_matches_clip_fps_for_fractional_rate() -> None:
    # 59.94 fps (60000/1001) must not be rounded differently inside zoompan: a rounded value
    # resolves to a different rational, and xfade rejects the frame-rate mismatch between an
    # animated clip and its neighbours ("input link frame rates do not match").
    base = _timeline()
    fractional = 60000 / 1001
    timeline = base.model_copy(update={"fps": fractional})
    second = timeline.clips[0].model_copy(
        update={
            "asset_path": Path("clip-b.mp4"),
            "timeline_start_s": 4.0,
            "transition_in": Transition(kind=TransitionType.SMOOTH_ZOOM, duration_s=0.25),
        }
    )
    timeline = timeline.model_copy(update={"clips": [timeline.clips[0], second]})

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert f":fps={fractional}" in filter_complex  # zoompan uses the exact clip fps
    assert ":fps=59.9401:" not in filter_complex  # not the rounded, mismatching rational


def test_long_held_clip_gets_subtle_pushin() -> None:
    # A long held shot (>= 4 s) gets a gentle push-in so it reads as motion, not a frozen frame.
    command = build_ffmpeg_command(_timeline(), output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "zoompan" in filter_complex


def test_held_shots_use_varied_push_anchors() -> None:
    # Consecutive held shots should push toward different anchors, not all dead-centre.
    base = _timeline()
    second = base.clips[0].model_copy(
        update={"asset_path": Path("clip-b.mp4"), "timeline_start_s": 4.0}
    )
    timeline = base.model_copy(update={"clips": [base.clips[0], second]})

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert filter_complex.count("zoompan") == 2
    assert "x='iw/2-(iw/zoom/2)'" in filter_complex  # clip 0 -> centre
    assert "x='iw-iw/zoom'" in filter_complex  # clip 1 -> a corner


def test_hero_clip_gets_a_deeper_pushin() -> None:
    # The hero shot pushes in further (cap 1.18) than a normal accent zoom (cap 1.12).
    hero = _timeline().clips[0].model_copy(update={"hero": True})
    timeline = _timeline().model_copy(update={"clips": [hero]})
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "zoompan" in filter_complex
    assert "1.18" in filter_complex  # the deeper hero zoom cap


def test_short_clip_has_no_pushin() -> None:
    short = _timeline().clips[0].model_copy(update={"source_end_s": 2.5})  # 1.5 s clip
    timeline = _timeline().model_copy(update={"clips": [short]})
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "zoompan" not in filter_complex


def test_slow_mo_clip_stretches_setpts() -> None:
    base = _timeline()
    slow = base.clips[0].model_copy(update={"speed": 0.75})
    timeline = base.model_copy(update={"clips": [slow]})

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "setpts=(PTS-STARTPTS)/0.75" in filter_complex


def test_whip_blur_uses_distinct_transition_name() -> None:
    base = _timeline()
    second = base.clips[0].model_copy(
        update={
            "asset_path": Path("clip-b.mp4"),
            "timeline_start_s": 4.0,
            "transition_in": Transition(kind=TransitionType.WHIP_BLUR, duration_s=0.2),
        }
    )
    timeline = base.model_copy(update={"clips": [base.clips[0], second]})

    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    filter_complex = command[command.index("-filter_complex") + 1]

    assert "transition=fadeblack" in filter_complex
    assert "transition=fade:" not in filter_complex
