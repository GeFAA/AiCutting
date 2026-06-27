from aicutting.director.drone_models import BeatPlan
from aicutting.director.edit_models import RhythmSlot

_DEFAULT_SLOT_S = 2.5
_INTRO_SLOT_S = 5.0  # length of each calm establishing slot covering the beatless intro
_BAR = 4  # beats per bar / downbeat cadence (build_beat_plan marks every 4th beat a downbeat)
_PHRASE = 16  # beats per phrase (build_beat_plan marks every 16th beat a phrase boundary)


def build_rhythm_grid(
    beat_plan: BeatPlan, target_duration_s: float, pace: float = 1.0
) -> list[RhythmSlot]:
    if not beat_plan.beats_s:
        return _visual_grid(target_duration_s)

    beats = [beat for beat in beat_plan.beats_s if beat < target_duration_s]
    if len(beats) < 2:
        return _visual_grid(target_duration_s)
    beats.append(min(target_duration_s, beats[-1] + (beats[-1] - beats[-2])))

    slots: list[RhythmSlot] = []
    # Cover the beatless intro (0 -> first beat) so the cumulative slot time stays the absolute
    # song time; otherwise every later cut is offset from its beat by the length of the intro.
    _add_intro_slots(slots, beats[0], beat_plan)
    # The style's `pace` retunes how long the mid/calm sections hold. Round to whole bars so the
    # downbeat snapping and phrase clamp below keep working; the drop span always stays one bar.
    mid_span = max(1, round(2 * pace)) * _BAR
    calm_span = max(1, round(3 * pace)) * _BAR
    index = 0
    while index < len(beats) - 1:
        start = beats[index]
        energy = _energy_at(beat_plan, start, target_duration_s)
        # Span whole bars (drop = 1 bar, calm ~3 bars at pace 1.0) and snap the cut to a downbeat so
        # it lands on a strong beat; never run a slot across a phrase boundary so the cut aligns
        # with the song's structural change.
        span = _BAR if energy >= 0.72 else mid_span if energy >= 0.45 else calm_span
        next_index = round((index + span) / _BAR) * _BAR
        next_index = min(next_index, ((index // _PHRASE) + 1) * _PHRASE)
        next_index = min(max(next_index, index + _BAR), len(beats) - 1)
        end = beats[next_index]
        if end <= start:
            break
        slots.append(
            RhythmSlot(
                index=len(slots),
                start_s=round(start, 3),
                end_s=round(end, 3),
                energy=round(energy, 6),
                is_accent=energy >= 0.72 or index % _PHRASE == 0,
                section=_section_at(beat_plan, start),
            )
        )
        index = next_index
    return slots or _visual_grid(target_duration_s)


def _add_intro_slots(slots: list[RhythmSlot], intro_end_s: float, beat_plan: BeatPlan) -> None:
    if intro_end_s <= 1.2:  # no meaningful intro before the first beat
        return
    cursor = 0.0
    while cursor < intro_end_s - 0.5:
        end = min(cursor + _INTRO_SLOT_S, intro_end_s)
        if end - cursor < 1.0:
            break
        slots.append(
            RhythmSlot(
                index=len(slots),
                start_s=round(cursor, 3),
                end_s=round(end, 3),
                energy=0.25,
                is_accent=False,
                section=_section_at(beat_plan, cursor),
            )
        )
        cursor = end


def _visual_grid(target_duration_s: float) -> list[RhythmSlot]:
    slots: list[RhythmSlot] = []
    cursor = 0.0
    while cursor + 0.5 < target_duration_s:
        end = min(cursor + _DEFAULT_SLOT_S, target_duration_s)
        if end - cursor < 1.0:
            break
        slots.append(
            RhythmSlot(
                index=len(slots),
                start_s=round(cursor, 3),
                end_s=round(end, 3),
                energy=0.4,
                is_accent=False,
                section="visual_default",
            )
        )
        cursor = end
    return slots


def _energy_at(beat_plan: BeatPlan, time_s: float, total_s: float) -> float:
    curve = beat_plan.energy_curve
    if not curve or total_s <= 0:
        return 0.4
    ratio = max(0.0, min(1.0, time_s / total_s))
    index = min(len(curve) - 1, int(round(ratio * (len(curve) - 1))))
    return float(curve[index])


def _section_at(beat_plan: BeatPlan, time_s: float) -> str:
    for section in beat_plan.sections:
        if section.start_s <= time_s < section.end_s:
            return section.label
    return beat_plan.sections[0].label if beat_plan.sections else "steady"
