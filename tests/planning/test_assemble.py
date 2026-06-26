from pathlib import Path

from aicutting.core.models import DroneShotType, MediaAsset, TransitionType
from aicutting.director.edit_models import (
    EditClip,
    EditDecision,
    FootageMoment,
    MomentRating,
    RhythmSlot,
)
from aicutting.planning.assemble import assemble_cut_plan, fallback_edit


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


def _moments(ids: list[str]) -> dict[str, FootageMoment]:
    return {
        mid: FootageMoment(moment_id=mid, asset_path=Path("flight.mp4"), timestamp_s=20.0 + i * 5)
        for i, mid in enumerate(ids)
    }


def test_assemble_fills_slots_and_clamps_windows() -> None:
    slots = _slots(3)
    moments = _moments(["m1", "m2", "m3"])
    media = [
        MediaAsset(path=Path("flight.mp4"), duration_s=60.0, width=1920, height=1080, fps=25.0)
    ]
    edit = EditDecision(
        arc="x",
        clips=[
            EditClip(slot_index=0, moment_id="m1", effect=TransitionType.HARD_CUT, reason="open"),
            EditClip(
                slot_index=1, moment_id="m2", effect=TransitionType.SMOOTH_ZOOM, reason="peak"
            ),
            EditClip(slot_index=2, moment_id="m3", effect=TransitionType.HARD_CUT, reason="rest"),
        ],
    )

    plan = assemble_cut_plan(edit, slots, moments, media)

    assert plan.style == "ai_drone_director_30"
    assert len(plan.timeline.clips) == 3
    assert round(plan.timeline.clips[0].timeline_duration_s, 3) == 3.0
    assert all(0 <= c.source_start_s < c.source_end_s <= 60.0 for c in plan.timeline.clips)
    assert plan.timeline.clips[1].transition_in.kind == TransitionType.SMOOTH_ZOOM


def test_assemble_skips_duplicate_moment() -> None:
    slots = _slots(2)
    moments = _moments(["m1"])
    media = [
        MediaAsset(path=Path("flight.mp4"), duration_s=60.0, width=1920, height=1080, fps=25.0)
    ]
    edit = EditDecision(
        arc="x",
        clips=[
            EditClip(slot_index=0, moment_id="m1", effect=TransitionType.HARD_CUT, reason="a"),
            EditClip(slot_index=1, moment_id="m1", effect=TransitionType.HARD_CUT, reason="dup"),
        ],
    )

    plan = assemble_cut_plan(edit, slots, moments, media)

    assert len(plan.timeline.clips) == 1  # duplicate dropped


def test_fallback_edit_assigns_without_repeats() -> None:
    slots = _slots(3)
    kept = [
        MomentRating(
            moment_id="m1", cinematic_score=0.9, shot_type=DroneShotType.REVEAL, keep=True,
            reason="",
        ),
        MomentRating(
            moment_id="m2", cinematic_score=0.8, shot_type=DroneShotType.APPROACH, keep=True,
            reason="",
        ),
        MomentRating(
            moment_id="m3", cinematic_score=0.7, shot_type=DroneShotType.ESTABLISHING, keep=True,
            reason="",
        ),
    ]
    edit = fallback_edit(kept, slots)
    chosen = [c.moment_id for c in edit.clips]
    assert len(chosen) == len(set(chosen))
    assert len(edit.clips) == 3


def test_fallback_edit_assigns_energy_effects() -> None:
    slots = _slots(2)  # slot 0 calm (not accent), slot 1 accent
    kept = [
        MomentRating(
            moment_id="m1", cinematic_score=0.9, shot_type=DroneShotType.REVEAL, keep=True,
            reason="",
        ),
        MomentRating(
            moment_id="m2", cinematic_score=0.8, shot_type=DroneShotType.ESTABLISHING, keep=True,
            reason="",
        ),
    ]
    edit = fallback_edit(kept, slots)
    effects = {clip.slot_index: clip.effect for clip in edit.clips}
    assert TransitionType.SMOOTH_ZOOM in effects.values()  # accent + energetic shot
    assert TransitionType.DISSOLVE in effects.values()  # calm + establishing shot
