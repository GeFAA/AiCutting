from aicutting.analysis.color import ColorSignature
from aicutting.core.models import TransitionType
from aicutting.director.edit_models import EditClip, EditDecision, MomentRating, RhythmSlot

_NEUTRAL_KEY = 0.5


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
    clips: list[EditClip] = []
    cursor = 0
    previous: str | None = None
    for index, slot in enumerate(slots):
        target = min(len(ordered) - 1, index * len(ordered) // len(slots))
        cursor = max(cursor, target)  # never travel backwards through the colour gradient
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


def _sort_key(rating: MomentRating, signatures: dict[str, ColorSignature]) -> tuple[float, float]:
    signature = signatures.get(rating.moment_id)
    if signature is None:
        return (_NEUTRAL_KEY, _NEUTRAL_KEY)
    return (signature.order_key, signature.brightness)
