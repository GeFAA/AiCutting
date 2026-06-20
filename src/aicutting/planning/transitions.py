from aicutting.core.models import ClipCandidate, Transition, TransitionType


def choose_transition(
    previous: ClipCandidate | None,
    current: ClipCandidate,
    beat_energy: float,
) -> Transition:
    if previous is None:
        return Transition(kind=TransitionType.HARD_CUT, duration_s=0.0)
    motion_delta = abs(previous.motion_score - current.motion_score)
    if beat_energy < 0.25 and motion_delta <= 0.1:
        return Transition(kind=TransitionType.DISSOLVE, duration_s=0.35)
    if beat_energy >= 0.75 and motion_delta <= 0.2:
        return Transition(kind=TransitionType.MATCH_CUT, duration_s=0.0)
    return Transition(kind=TransitionType.HARD_CUT, duration_s=0.0)
