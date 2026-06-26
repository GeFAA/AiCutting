from dataclasses import dataclass

import numpy as np

from aicutting.analysis.motion import analyze_motion_frames, reject_bad_motion
from aicutting.core.models import DroneShotType


@dataclass(frozen=True)
class DroneShotAnalysis:
    shot_type: DroneShotType
    technical_score: float
    stability_score: float
    composition_score: float
    motion_intent_score: float
    reveal_score: float
    novelty_score: float
    drone_director_score: float
    rejection_reason: str | None
    reasons: list[str]


def analyze_drone_shot_frames(
    frames: list[np.ndarray],
    starts_near_clip_edge: bool,
) -> DroneShotAnalysis:
    motion = analyze_motion_frames(frames)
    rejection = reject_bad_motion(motion, starts_near_clip_edge=starts_near_clip_edge)
    # Drone-domain refinement: heavy "searching" motion is search-flight, not generic
    # instability. reject_bad_motion can label it "unstable_yaw_or_pan" purely because its
    # jitter threshold is checked before the searching branch; reclassify it here unless the
    # edge heuristic already identified takeoff/landing.
    if rejection != "takeoff_or_landing_motion" and motion.movement_type == "searching":
        rejection = "search_flight_before_subject"

    # A reveal is a smooth, purposeful sweep that opens up the scene. Pixel first/last deltas
    # are unreliable on small subjects, so score it from motion smoothness and movement.
    reveal = round(motion.smoothness_score * motion.movement_score, 6)
    novelty = _novelty_score(frames)
    technical = _technical_score(frames)
    motion_intent = max(
        0.0, min(1.0, (motion.smoothness_score * 0.6) + (motion.movement_score * 0.4))
    )
    shot_type = _shot_type(motion.movement_type, reveal, rejection)
    if rejection == "takeoff_or_landing_motion":
        shot_type = DroneShotType.TAKEOFF_OR_LANDING
    elif rejection == "search_flight_before_subject":
        shot_type = DroneShotType.SEARCH_MOTION
    elif rejection is not None:
        shot_type = DroneShotType.UNSTABLE

    score = round(
        (technical * 0.18)
        + (motion.smoothness_score * 0.24)
        + (motion.composition_score * 0.18)
        + (motion_intent * 0.18)
        + (reveal * 0.14)
        + (novelty * 0.08),
        6,
    )
    if rejection is not None:
        score = round(min(score, 0.45), 6)

    reasons = [
        f"{shot_type.value} motion",
        f"smoothness {motion.smoothness_score:.2f}",
        f"reveal {reveal:.2f}",
    ]
    if rejection:
        reasons.append(rejection)

    return DroneShotAnalysis(
        shot_type=shot_type,
        technical_score=technical,
        stability_score=motion.smoothness_score,
        composition_score=motion.composition_score,
        motion_intent_score=round(motion_intent, 6),
        reveal_score=reveal,
        novelty_score=novelty,
        drone_director_score=score,
        rejection_reason=rejection,
        reasons=reasons,
    )


def _shot_type(movement_type: str, reveal_score: float, rejection: str | None) -> DroneShotType:
    if rejection is not None:
        return DroneShotType.UNSTABLE
    if reveal_score >= 0.6:
        return DroneShotType.REVEAL
    if movement_type == "hover":
        return DroneShotType.ESTABLISHING
    if movement_type in {"pan_left", "pan_right"}:
        return DroneShotType.TRACKING
    if movement_type == "tilt_down":
        return DroneShotType.TOP_DOWN
    if movement_type == "tilt_up":
        return DroneShotType.PULL_BACK
    if movement_type == "push_in":
        return DroneShotType.APPROACH
    return DroneShotType.UNKNOWN


def _technical_score(frames: list[np.ndarray]) -> float:
    if not frames:
        return 0.0
    values = [float(frame.std()) / 80.0 for frame in frames]
    return round(max(0.0, min(1.0, float(np.mean(values)))), 6)


def _novelty_score(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.0
    diffs = [
        float(np.mean(np.abs(current.astype(np.float32) - previous.astype(np.float32)))) / 90.0
        for previous, current in zip(frames, frames[1:], strict=False)
    ]
    return round(max(0.0, min(1.0, float(np.mean(diffs)))), 6)
