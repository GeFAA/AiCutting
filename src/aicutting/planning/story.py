from pathlib import Path

from aicutting.core.models import ClipCandidate, DroneShotType
from aicutting.director.drone_models import BeatPlan, StoryPlan, StoryPlanClip

ROLE_PREFERENCES: dict[str, set[DroneShotType]] = {
    "establish": {DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN, DroneShotType.REVEAL},
    "move": {
        DroneShotType.APPROACH,
        DroneShotType.FLY_THROUGH,
        DroneShotType.TRACKING,
        DroneShotType.ORBIT,
    },
    "peak": {DroneShotType.REVEAL, DroneShotType.APPROACH, DroneShotType.FLY_THROUGH},
    "release": {DroneShotType.PULL_BACK, DroneShotType.ESTABLISHING, DroneShotType.TOP_DOWN},
}

# Roles are emitted in narrative order, but picked in priority order: the climax claims its
# standout shot (e.g. the best reveal) before "establish" — which also lists REVEAL — can take it.
PICK_ORDER = ("peak", "establish", "move", "release")
EMIT_ORDER = ("establish", "move", "peak", "release")

BAD_TYPES = {
    DroneShotType.SEARCH_MOTION,
    DroneShotType.TAKEOFF_OR_LANDING,
    DroneShotType.UNSTABLE,
}


def build_story_plan(
    candidates: list[ClipCandidate],
    beat_plan: BeatPlan,
    target_duration_s: float,
) -> StoryPlan:
    usable = [
        candidate
        for candidate in candidates
        if candidate.shot_type not in BAD_TYPES and not candidate.rejection_reason
    ]
    if not usable:
        usable = sorted(candidates, key=lambda candidate: candidate.director_score, reverse=True)

    chosen: dict[str, ClipCandidate] = {}
    used_windows: set[tuple[Path, float, float]] = set()
    for role in PICK_ORDER:
        candidate = _pick_for_role(role, usable, used_windows)
        if candidate is None:
            continue
        chosen[role] = candidate
        used_windows.add((candidate.asset_path, candidate.start_s, candidate.end_s))

    selected: list[StoryPlanClip] = []
    for role in EMIT_ORDER:
        candidate = chosen.get(role)
        if candidate is None:
            continue
        selected.append(
            StoryPlanClip(
                asset_path=candidate.asset_path,
                source_start_s=candidate.start_s,
                source_end_s=candidate.end_s,
                role=role,
                shot_type=candidate.shot_type,
                beat_anchor_s=_beat_anchor(beat_plan, role),
                reason=f"{role}: {candidate.shot_type.value} score {candidate.director_score:.2f}",
            )
        )
    return StoryPlan(target_duration_s=target_duration_s, clips=selected)


def _pick_for_role(
    role: str,
    candidates: list[ClipCandidate],
    used_windows: set[tuple[Path, float, float]],
) -> ClipCandidate | None:
    preferred = ROLE_PREFERENCES[role]
    # Dedup at the window level, not the file level: drone footage is often one long clip,
    # and distinct windows of the same file are still distinct shots for different roles.
    pool = [
        candidate
        for candidate in candidates
        if (candidate.asset_path, candidate.start_s, candidate.end_s) not in used_windows
    ]
    if not pool:
        pool = candidates
    return max(
        pool,
        key=lambda candidate: (
            candidate.shot_type in preferred,
            candidate.reveal_score or 0.0,
            candidate.director_score,
        ),
        default=None,
    )


def _beat_anchor(beat_plan: BeatPlan, role: str) -> float | None:
    if not beat_plan.downbeats_s:
        return None
    if role == "peak":
        return beat_plan.downbeats_s[
            min(len(beat_plan.downbeats_s) - 1, len(beat_plan.downbeats_s) // 2)
        ]
    if role == "release":
        return beat_plan.downbeats_s[-1]
    return beat_plan.downbeats_s[0]
