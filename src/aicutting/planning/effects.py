from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.drone_models import BeatPlan, EffectDecision, EffectPlan, StoryPlan


def build_effect_plan(story: StoryPlan, beat_plan: BeatPlan) -> EffectPlan:
    decisions: list[EffectDecision] = []
    energy = _dominant_energy(beat_plan)
    for index, clip in enumerate(story.clips):
        if index == 0:
            previous_type: DroneShotType | None = None
            transition = TransitionType.HARD_CUT
            duration = 0.0
            confidence = 1.0
            reason = "first clip starts clean"
        else:
            previous_type = story.clips[index - 1].shot_type
            transition, duration, confidence, reason = _transition(
                previous_type, clip.shot_type, energy
            )
        decisions.append(
            EffectDecision(
                clip_index=index,
                transition=transition,
                duration_s=duration,
                confidence=confidence,
                beat_anchor_s=clip.beat_anchor_s,
                source_shot_type=previous_type,
                target_shot_type=clip.shot_type,
                reason=reason,
            )
        )
    return EffectPlan(decisions=decisions)


def _dominant_energy(beat_plan: BeatPlan) -> float:
    if not beat_plan.sections:
        return 0.2
    return max(section.energy for section in beat_plan.sections)


def _transition(
    previous: DroneShotType,
    current: DroneShotType,
    energy: float,
) -> tuple[TransitionType, float, float, str]:
    if energy >= 0.72 and current in {
        DroneShotType.APPROACH,
        DroneShotType.REVEAL,
        DroneShotType.FLY_THROUGH,
    }:
        return TransitionType.SMOOTH_ZOOM, 0.25, 0.82, "forward/reveal motion on high-energy beat"
    if energy >= 0.78 and previous in {DroneShotType.TRACKING, DroneShotType.ORBIT}:
        return TransitionType.WHIP_BLUR, 0.18, 0.76, "lateral motion supports whip blur"
    if energy <= 0.35 and current in {
        DroneShotType.PULL_BACK,
        DroneShotType.ESTABLISHING,
        DroneShotType.TOP_DOWN,
    }:
        return TransitionType.DISSOLVE, 0.35, 0.8, "calm scenic release"
    if energy >= 0.82:
        return TransitionType.FLASH_CUT, 0.08, 0.7, "high-energy accent"
    return TransitionType.HARD_CUT, 0.0, 0.9, "clean beat cut fallback"
