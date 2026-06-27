from pathlib import Path

from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import (
    AudioAnalysis,
    MediaAsset,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)
from aicutting.core.style import STYLE_PRESETS, resolve_style
from aicutting.director.edit_models import EditClip, EditDecision, FootageMoment, RhythmSlot
from aicutting.planning.assemble import (
    _SLOW_MO,
    _SLOW_MO_ENERGY,
    _TRANSITION_ENERGY,
    assemble_cut_plan,
)
from aicutting.planning.rhythm import build_rhythm_grid
from aicutting.render.ffmpeg import build_ffmpeg_command

# --- resolve_style mapping -------------------------------------------------------------------


def test_resolve_style_maps_known_names_case_insensitively() -> None:
    assert resolve_style("epic").name == "epic"
    assert resolve_style("CHILL").name == "chill"
    assert resolve_style("  Vlog  ").name == "vlog"
    assert resolve_style("cinematic").name == "cinematic"


def test_resolve_style_unknown_falls_back_to_cinematic() -> None:
    fallback = resolve_style("does-not-exist")
    assert fallback is STYLE_PRESETS["cinematic"]
    assert fallback.name == "cinematic"


def test_cinematic_preset_matches_the_shipped_constants() -> None:
    # The default preset must equal the values the pipeline shipped with, so cinematic is a no-op.
    cinematic = STYLE_PRESETS["cinematic"]
    assert cinematic.pace == 1.0
    assert cinematic.slow_mo_speed == _SLOW_MO
    assert cinematic.slow_mo_energy == _SLOW_MO_ENERGY
    assert cinematic.transition_energy == _TRANSITION_ENERGY
    assert cinematic.grade_strength == 1.0


# --- pace: chill holds longer than epic ------------------------------------------------------


def _calm_grid(pace: float) -> list[RhythmSlot]:
    beats = [i * 0.5 for i in range(160)]  # 80 s of steady beats
    audio = AudioAnalysis(path=None, duration_s=80.0, beats_s=beats, energy=[0.1])  # all calm
    return build_rhythm_grid(build_beat_plan(audio), target_duration_s=80.0, pace=pace)


def test_chill_calm_spans_are_longer_than_epic() -> None:
    chill = _calm_grid(STYLE_PRESETS["chill"].pace)
    epic = _calm_grid(STYLE_PRESETS["epic"].pace)
    assert max(slot.duration_s for slot in chill) > max(slot.duration_s for slot in epic)


def test_default_pace_reproduces_the_cinematic_grid() -> None:
    beats = [i * 0.5 for i in range(160)]
    audio = AudioAnalysis(path=None, duration_s=80.0, beats_s=beats, energy=[0.5])
    plan = build_beat_plan(audio)
    assert build_rhythm_grid(plan, 80.0) == build_rhythm_grid(plan, 80.0, pace=1.0)


# --- slow-mo + transitions: vlog is punchy hard cuts -----------------------------------------


def _slots(count: int) -> list[RhythmSlot]:
    return [
        RhythmSlot(
            index=i,
            start_s=float(i * 3),
            end_s=float(i * 3 + 3),
            energy=0.8 if i % 2 else 0.2,
            is_accent=bool(i % 2),
            section="s",
        )
        for i in range(count)
    ]


def _hard_cut_edit(count: int) -> EditDecision:
    return EditDecision(
        arc="x",
        clips=[
            EditClip(slot_index=i, moment_id=f"m{i + 1}", effect=TransitionType.HARD_CUT, reason="")
            for i in range(count)
        ],
    )


def _moments(count: int) -> dict[str, FootageMoment]:
    return {
        f"m{i + 1}": FootageMoment(
            moment_id=f"m{i + 1}", asset_path=Path("flight.mp4"), timestamp_s=20.0 + i * 5
        )
        for i in range(count)
    }


def _media() -> list[MediaAsset]:
    return [
        MediaAsset(path=Path("flight.mp4"), duration_s=120.0, width=1920, height=1080, fps=25.0)
    ]


def test_vlog_yields_only_hard_cuts_and_full_speed() -> None:
    vlog = STYLE_PRESETS["vlog"]
    plan = assemble_cut_plan(
        _hard_cut_edit(4),
        _slots(4),
        _moments(4),
        _media(),
        slow_mo_speed=vlog.slow_mo_speed,
        slow_mo_energy=vlog.slow_mo_energy,
        transition_energy=vlog.transition_energy,
    )

    assert all(clip.transition_in.kind == TransitionType.HARD_CUT for clip in plan.timeline.clips)
    assert all(clip.speed == 1.0 for clip in plan.timeline.clips)


def test_cinematic_assemble_still_adds_a_crossfade_and_slow_mo() -> None:
    # Guards the contrast above: with the default (cinematic) knobs the same montage gets a
    # crossfade and a slowed calm clip, proving the vlog result is a real change, not a no-op.
    plan = assemble_cut_plan(_hard_cut_edit(4), _slots(4), _moments(4), _media())

    assert any(clip.transition_in.kind != TransitionType.HARD_CUT for clip in plan.timeline.clips)
    assert any(clip.speed < 1.0 for clip in plan.timeline.clips)


# --- grade: Timeline.grade_strength flows into the ffmpeg filter ------------------------------


def _grade_timeline(grade_strength: float) -> Timeline:
    return Timeline(
        target_duration_s=4.0,
        fps=25.0,
        width=1920,
        height=1080,
        grade_strength=grade_strength,
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


def _filter_complex(timeline: Timeline) -> str:
    command = build_ffmpeg_command(timeline, output_path=Path("out/final.mp4"), music_path=None)
    return command[command.index("-filter_complex") + 1]


def test_grade_strength_flows_into_the_ffmpeg_filter() -> None:
    default = _filter_complex(_grade_timeline(1.0))
    assert "eq=contrast=1.06:saturation=1.1" in default  # strength 1.0 == the shipped grade

    stronger = _filter_complex(_grade_timeline(1.4))  # epic-style stronger grade
    assert "eq=contrast=1.084:saturation=1.14" in stronger

    neutral = _filter_complex(_grade_timeline(0.0))  # vlog leans toward this neutral look
    assert "eq=contrast=1:saturation=1" in neutral
    assert "rs=0:bs=0:rh=0:bh=0" in neutral  # no teal-orange split-tone, and no `-0`


def test_timeline_grade_strength_defaults_to_one() -> None:
    bare = Timeline(
        target_duration_s=4.0, fps=25.0, width=1920, height=1080, clips=_grade_timeline(1.0).clips
    )
    assert bare.grade_strength == 1.0  # the field defaults to the cinematic grade
