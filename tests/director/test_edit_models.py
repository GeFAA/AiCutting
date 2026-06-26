from pathlib import Path

from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.edit_models import (
    ContactSheet,
    EditClip,
    EditDecision,
    FootageMoment,
    MomentRating,
    RhythmSlot,
)


def test_rhythm_slot_exposes_duration() -> None:
    slot = RhythmSlot(index=0, start_s=2.0, end_s=5.0, energy=0.8, is_accent=True, section="peak")
    assert slot.duration_s == 3.0


def test_edit_decision_round_trips() -> None:
    moment = FootageMoment(moment_id="m001", asset_path=Path("a.mp4"), timestamp_s=12.0)
    sheet = ContactSheet(path=Path("sheet-1.jpg"), moment_ids=["m001"])
    rating = MomentRating(
        moment_id="m001",
        cinematic_score=0.9,
        shot_type=DroneShotType.REVEAL,
        keep=True,
        reason="strong reveal",
    )
    decision = EditDecision(
        arc="calm build to reveal",
        clips=[
            EditClip(
                slot_index=0,
                moment_id="m001",
                effect=TransitionType.SMOOTH_ZOOM,
                reason="peak",
            )
        ],
    )

    assert moment.moment_id == "m001"
    assert sheet.moment_ids == ["m001"]
    assert rating.keep is True
    assert decision.clips[0].effect == TransitionType.SMOOTH_ZOOM
