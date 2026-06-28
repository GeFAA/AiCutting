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


def _accent_slot() -> list[RhythmSlot]:
    return [RhythmSlot(index=0, start_s=0.0, end_s=3.0, energy=0.9, is_accent=True, section="peak")]


def test_arc_prefers_dynamic_shots_on_an_accent_within_the_same_colour() -> None:
    # two near-identical colours: an establishing and a reveal. On an accent (the drop), the arc
    # should take the dynamic reveal -- without moving along the colour journey.
    kept = [
        _rating("estab", DroneShotType.ESTABLISHING),
        _rating("reveal", DroneShotType.REVEAL),
    ]
    signatures = {
        "estab": ColorSignature(greenness=0.30, brightness=0.4, saturation=0.3),
        "reveal": ColorSignature(greenness=0.31, brightness=0.4, saturation=0.3),
    }

    chosen = color_ordered_edit(kept, signatures, _accent_slot()).clips[0].moment_id
    assert chosen == "reveal"


def test_arc_prefers_establishing_on_a_calm_slot_within_the_same_colour() -> None:
    kept = [
        _rating("reveal", DroneShotType.REVEAL),
        _rating("estab", DroneShotType.ESTABLISHING),
    ]
    signatures = {
        "reveal": ColorSignature(greenness=0.30, brightness=0.4, saturation=0.3),
        "estab": ColorSignature(greenness=0.31, brightness=0.4, saturation=0.3),
    }

    chosen = color_ordered_edit(kept, signatures, _slots(1)).clips[0].moment_id
    assert chosen == "estab"


def test_arc_never_swaps_across_a_colour_gap() -> None:
    # a dynamic shot two shades greener must NOT be pulled onto an early accent (would break the
    # journey); the colour gap is far larger than the same-shade epsilon.
    kept = [
        _rating("lava_estab", DroneShotType.ESTABLISHING),
        _rating("green_reveal", DroneShotType.REVEAL),
    ]
    signatures = {
        "lava_estab": ColorSignature(greenness=0.05, brightness=0.2, saturation=0.1),
        "green_reveal": ColorSignature(greenness=0.6, brightness=0.5, saturation=0.5),
    }

    chosen = color_ordered_edit(kept, signatures, _accent_slot()).clips[0].moment_id
    assert chosen == "lava_estab"  # colour journey wins over the section match


def test_color_ordered_edit_fills_every_slot() -> None:
    slots = _slots(5)
    kept = [_rating("a", DroneShotType.ORBIT), _rating("b", DroneShotType.REVEAL)]
    signatures = {
        "a": ColorSignature(greenness=0.1, brightness=0.3, saturation=0.2),
        "b": ColorSignature(greenness=0.5, brightness=0.5, saturation=0.4),
    }

    assert len(color_ordered_edit(kept, signatures, slots).clips) == 5
