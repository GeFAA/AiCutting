from pathlib import Path

from aicutting.core.models import (
    CutPlan,
    DroneShotType,
    MediaAsset,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)
from aicutting.director.edit_models import (
    EditClip,
    EditDecision,
    FootageMoment,
    MomentRating,
    RhythmSlot,
)

_CALM = {DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN, DroneShotType.ORBIT}
_ENERGETIC = {DroneShotType.REVEAL, DroneShotType.APPROACH, DroneShotType.FLY_THROUGH}
_REUSE_SPACING = 5  # avoid reusing a moment within this many slots while fresh ones remain
_SLOW_MO = 0.75  # playback speed for calm establishing shots (a dreamy slow drift)
_SLOW_MO_ENERGY = 0.3  # slow-mo only the genuinely calm slots; drops stay full speed
_TRANSITION_ENERGY = 0.4  # crossfade calm cuts quieter than this; energetic drops stay hard cuts


def fallback_edit(kept: list[MomentRating], slots: list[RhythmSlot]) -> EditDecision:
    pool = sorted(kept, key=lambda rating: rating.cinematic_score, reverse=True)
    if not pool:
        return EditDecision(arc="deterministic fill", clips=[])
    recent: list[str] = []
    prev: DroneShotType | None = None
    clips: list[EditClip] = []
    for slot in slots:
        prefer = _ENERGETIC if slot.is_accent else _CALM
        choice = _pick(pool, recent, prev, prefer)
        recent.append(choice.moment_id)
        if len(recent) > _REUSE_SPACING:
            recent.pop(0)
        prev = choice.shot_type
        clips.append(
            EditClip(
                slot_index=slot.index,
                moment_id=choice.moment_id,
                effect=_fallback_effect(slot, choice.shot_type),
                reason=f"{choice.shot_type.value} fill",
            )
        )
    return EditDecision(arc="deterministic fill", clips=clips)


def _fallback_effect(slot: RhythmSlot, shot_type: DroneShotType) -> TransitionType:
    if slot.is_accent and shot_type in _ENERGETIC:
        return TransitionType.SMOOTH_ZOOM
    if slot.energy <= 0.35 and shot_type in _CALM:
        return TransitionType.DISSOLVE
    return TransitionType.HARD_CUT


def _accent_transition(count: int) -> TransitionType:
    # Cohesive gentle crossfades that fit aerial footage (no jarring whips/slides); the SMOOTH_ZOOM
    # variant also pushes in slightly. Both render as a soft crossfade.
    return TransitionType.SMOOTH_ZOOM if count % 2 else TransitionType.DISSOLVE


def _pick(
    pool: list[MomentRating],
    recent: list[str],
    prev: DroneShotType | None,
    prefer: set[DroneShotType],
) -> MomentRating:
    fresh = [r for r in pool if r.moment_id not in recent and r.shot_type != prev]
    if not fresh:
        fresh = [r for r in pool if r.moment_id not in recent]
    if not fresh:
        fresh = pool  # the whole pool is recently used -> reuse the strongest
    return max(fresh, key=lambda r: (r.shot_type in prefer, r.cinematic_score))


def assemble_cut_plan(
    edit: EditDecision,
    slots: list[RhythmSlot],
    moments: dict[str, FootageMoment],
    media: list[MediaAsset],
    trim_s: float = 12.0,
    slow_mo_speed: float = _SLOW_MO,
    slow_mo_energy: float = _SLOW_MO_ENERGY,
    transition_energy: float = _TRANSITION_ENERGY,
) -> CutPlan:
    durations = {asset.path: asset.duration_s for asset in media}
    by_slot = {clip.slot_index: clip for clip in edit.clips}
    base = media[0]
    pool = _moment_pool(edit, moments)
    clips: list[TimelineClip] = []
    cursor = 0.0
    use_count: dict[str, int] = {}
    recent: list[str] = []
    prev_effect: TransitionType | None = None
    since_transition = 2  # clips since the last transition (start ready so the first one can fire)
    transition_count = 0
    for position, slot in enumerate(slots):
        clip = by_slot.get(slot.index)
        effect = clip.effect if clip is not None else TransitionType.HARD_CUT
        if position == 0:
            effect = TransitionType.HARD_CUT  # first clip is the chain base, no rendered transition
        else:
            # Let gentle crossfades flow through the calm sections; leave the energetic drops as
            # punchy hard cuts on the beat (a dissolve on a drop feels wrong). Space them out so
            # transitions stay tasteful instead of constant.
            if (
                effect == TransitionType.HARD_CUT
                and slot.energy < transition_energy
                and since_transition >= 2
            ):
                effect = _accent_transition(transition_count)
                transition_count += 1
            if effect == prev_effect and effect != TransitionType.HARD_CUT:
                effect = TransitionType.HARD_CUT  # never the same transition twice in a row
        # An xfade overlaps its two clips, so the clip must be longer than the slot by the overlap
        # for the post-fade timeline to keep landing exactly on the beat.
        overlap = _effect_duration(effect) if position > 0 else 0.0
        # Slow-mo the calm establishing shots: take a shorter source window and slow it to fill the
        # slot, so the cut still lands exactly on the beat (timeline_duration = source / speed).
        # Energetic drops stay full speed and punchy.
        speed = slow_mo_speed if slot.energy <= slow_mo_energy else 1.0
        choice = _choose_moment(
            clip, moments, pool, recent, use_count,
            (slot.duration_s + overlap) * speed, durations, trim_s,
        )
        if choice is None:
            continue
        moment_id, (start_s, end_s) = choice
        clips.append(
            TimelineClip(
                asset_path=moments[moment_id].asset_path,
                source_start_s=start_s,
                source_end_s=end_s,
                timeline_start_s=round(cursor, 3),
                transition_in=Transition(kind=effect, duration_s=overlap),
                speed=speed,
                color_intent="subtle_cinematic",
            )
        )
        use_count[moment_id] = use_count.get(moment_id, 0) + 1
        recent.append(moment_id)
        if len(recent) > _REUSE_SPACING:
            recent.pop(0)
        since_transition = 0 if effect != TransitionType.HARD_CUT else since_transition + 1
        prev_effect = effect
        cursor = round(cursor + slot.duration_s, 3)  # net render contribution -> cuts stay on beat

    target = round(cursor, 3)
    if target <= 0:
        target = slots[-1].end_s if slots else 1.0
    timeline = Timeline(
        target_duration_s=target, clips=clips, fps=base.fps, width=base.width, height=base.height
    )
    return CutPlan(
        target_duration_s=target,
        style="ai_drone_director_30",
        timeline=timeline,
        notes=[f"Generated by the AI Drone Director ({len(clips)} clips). Arc: {edit.arc}"],
    )


def _moment_pool(edit: EditDecision, moments: dict[str, FootageMoment]) -> list[str]:
    ordered: list[str] = []
    for clip in edit.clips:
        if clip.moment_id in moments and clip.moment_id not in ordered:
            ordered.append(clip.moment_id)
    return ordered or list(moments.keys())


def _choose_moment(
    clip: EditClip | None,
    moments: dict[str, FootageMoment],
    pool: list[str],
    recent: list[str],
    use_count: dict[str, int],
    need_s: float,
    durations: dict[Path, float],
    trim_s: float,
) -> tuple[str, tuple[float, float]] | None:
    # Honour the agent's pick when it is fresh; otherwise substitute the least-used unseen moment;
    # only as a last resort reuse a recent one. Every branch must yield a full-length window so the
    # slot is filled and the beat grid stays intact.
    by_use = sorted(pool, key=lambda mid: (use_count.get(mid, 0), mid))
    preferred = [clip.moment_id] if clip is not None and clip.moment_id in moments else []
    candidates = [
        *(m for m in preferred if m not in recent),
        *(m for m in by_use if m not in recent),
        *preferred,
        *by_use,
    ]
    seen: set[str] = set()
    for moment_id in candidates:
        if moment_id in seen:
            continue
        seen.add(moment_id)
        moment = moments[moment_id]
        window = _exact_window(
            moment.timestamp_s,
            need_s,
            durations.get(moment.asset_path, 0.0),
            trim_s,
            use_count.get(moment_id, 0),
        )
        if window is not None:
            return moment_id, window
    return None


def _exact_window(
    timestamp_s: float, need_s: float, file_duration_s: float, trim_s: float, reuse: int
) -> tuple[float, float] | None:
    # Return a window of EXACTLY need_s seconds (offset on reuse so a repeated moment shows
    # different footage), or None if even the raw file is too short for this slot.
    if file_duration_s <= 0 or need_s <= 0:
        return None
    low = min(trim_s, file_duration_s * 0.1)
    high = max(low + 0.1, file_duration_s - low)
    if high - low < need_s:  # safe zone too small; relax toward the raw file if it is long enough
        if file_duration_s < need_s + 0.2:
            return None
        low, high = 0.0, file_duration_s
    start = timestamp_s + reuse * 0.6 - need_s / 2
    start = min(max(low, start), high - need_s)
    return round(start, 3), round(start + need_s, 3)


def _effect_duration(effect: TransitionType) -> float:
    if effect == TransitionType.DISSOLVE:
        return 0.35
    if effect in {TransitionType.SMOOTH_ZOOM, TransitionType.WHIP_BLUR}:
        return 0.25
    return 0.0
