from aicutting.analysis.color import ColorSignature
from aicutting.core.models import DroneShotType
from aicutting.director.edit_models import MomentRating, RhythmSlot
from aicutting.planning.sequence import color_ordered_edit


def _slots(count: int) -> list[RhythmSlot]:
    return [
        RhythmSlot(
            index=i, start_s=float(i * 3), end_s=float(i * 3 + 3), energy=0.4, is_accent=False,
            section="s",
        )
        for i in range(count)
    ]


def _rating(moment_id: str, shot: DroneShotType) -> MomentRating:
    return MomentRating(
        moment_id=moment_id, cinematic_score=0.8, shot_type=shot, keep=True, reason=""
    )


def test_color_ordered_edit_puts_lava_before_green() -> None:
    slots = _slots(6)
    kept = [
        _rating("green", DroneShotType.ORBIT),
        _rating("lava", DroneShotType.ESTABLISHING),
        _rating("mid", DroneShotType.REVEAL),
    ]
    signatures = {
        "green": ColorSignature(greenness=0.6, brightness=0.5, saturation=0.5),
        "lava": ColorSignature(greenness=0.02, brightness=0.2, saturation=0.1),
        "mid": ColorSignature(greenness=0.25, brightness=0.4, saturation=0.3),
    }

    order = [clip.moment_id for clip in color_ordered_edit(kept, signatures, slots).clips]

    assert order.index("lava") < order.index("mid") < order.index("green")
    assert all(order[i] != order[i + 1] for i in range(len(order) - 1))  # no adjacent repeats


def test_color_ordered_edit_fills_every_slot() -> None:
    slots = _slots(5)
    kept = [_rating("a", DroneShotType.ORBIT), _rating("b", DroneShotType.REVEAL)]
    signatures = {
        "a": ColorSignature(greenness=0.1, brightness=0.3, saturation=0.2),
        "b": ColorSignature(greenness=0.5, brightness=0.5, saturation=0.4),
    }

    assert len(color_ordered_edit(kept, signatures, slots).clips) == 5
