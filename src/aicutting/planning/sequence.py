from aicutting.analysis.color import ColorSignature
from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.edit_models import EditClip, EditDecision, MomentRating, RhythmSlot

_NEUTRAL_KEY = 0.5

# Musical-structure arc: scene-setting shots suit the calm sections, dynamic shots suit the drops.
_ESTABLISHING = {DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN, DroneShotType.ORBIT}
_DYNAMIC = {
    DroneShotType.REVEAL,
    DroneShotType.APPROACH,
    DroneShotType.FLY_THROUGH,
    DroneShotType.TRACKING,
}
# Two shots count as "the same shade" (so swapping them does not disturb the colour journey) when
# their colour keys are within this much.
_SAME_SHADE = 0.06


def color_ordered_edit(
    kept: list[MomentRating],
    signatures: dict[str, ColorSignature],
    slots: list[RhythmSlot],
) -> EditDecision:
    # Order the kept moments into a coherent colour journey (dark lava -> green moss) and lay them
    # onto the beat grid in that order, so similar-looking shots stay together instead of jumping
    # between scene types. The grid still drives clip length (calm = long, drops = fast) and the
    # assembler keeps every cut on the beat; this only decides WHICH shot goes where.
    if not kept or not slots:
        return EditDecision(arc="colour journey", clips=[])
    ordered = sorted(kept, key=lambda rating: _sort_key(rating, signatures))
    keys = [_sort_key(rating, signatures)[0] for rating in ordered]  # colour-journey position
    clips: list[EditClip] = []
    cursor = 0
    previous: str | None = None
    for index, slot in enumerate(slots):
        target = min(len(ordered) - 1, index * len(ordered) // len(slots))
        cursor = max(cursor, target)  # never travel backwards through the colour gradient
        cursor = _arc_swap(ordered, keys, cursor, slot, previous)
        if ordered[cursor].moment_id == previous:
            # never the same shot in two adjacent slots (reads as a glitch); step forward, or at
            # the tail of the journey alternate with the previous shade.
            if cursor + 1 < len(ordered):
                cursor += 1
            elif cursor - 1 >= 0:
                cursor -= 1
        choice = ordered[cursor]
        previous = choice.moment_id
        clips.append(
            EditClip(
                slot_index=slot.index,
                moment_id=choice.moment_id,
                effect=TransitionType.HARD_CUT,
                reason=choice.shot_type.value,
            )
        )
    return EditDecision(arc="colour-coherent journey: lava -> green", clips=clips)


def _arc_swap(
    ordered: list[MomentRating],
    keys: list[float],
    cursor: int,
    slot: RhythmSlot,
    previous: str | None,
) -> int:
    # Arc tie-break: if the next moment is the same colour shade (so the journey is undisturbed) and
    # fits this slot's section better -- a dynamic shot on a drop, an establishing shot on a calm
    # cut -- step onto it. Big colour gaps are never crossed: the journey always wins over the arc.
    nxt = cursor + 1
    if nxt >= len(ordered) or abs(keys[nxt] - keys[cursor]) > _SAME_SHADE:
        return cursor
    preferred = _DYNAMIC if slot.is_accent else _ESTABLISHING
    fits_next = ordered[nxt].shot_type in preferred
    fits_here = ordered[cursor].shot_type in preferred
    if fits_next and not fits_here and ordered[nxt].moment_id != previous:
        return nxt
    return cursor


def _sort_key(rating: MomentRating, signatures: dict[str, ColorSignature]) -> tuple[float, float]:
    signature = signatures.get(rating.moment_id)
    if signature is None:
        return (_NEUTRAL_KEY, _NEUTRAL_KEY)
    return (signature.order_key, signature.brightness)
