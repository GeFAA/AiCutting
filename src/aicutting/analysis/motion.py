from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class MotionAnalysis:
    smoothness_score: float
    jitter_score: float
    movement_score: float
    composition_score: float
    usability_score: float
    movement_type: str


def analyze_motion_frames(frames: list[np.ndarray]) -> MotionAnalysis:
    if len(frames) < 2:
        return MotionAnalysis(0.4, 0.2, 0.2, 0.5, 0.45, "unknown")

    centers = [_bright_center(frame) for frame in frames]
    vectors = [
        (current[0] - previous[0], current[1] - previous[1])
        for previous, current in zip(centers, centers[1:], strict=False)
    ]
    magnitudes = np.array([float(np.hypot(dx, dy)) for dx, dy in vectors], dtype=float)
    if magnitudes.size == 0:
        return MotionAnalysis(0.4, 0.2, 0.2, 0.5, 0.45, "unknown")

    mean_motion = float(np.mean(magnitudes))
    motion_variance = float(np.std(magnitudes))
    direction_changes = _direction_change_ratio(vectors)
    jitter = min(1.0, (motion_variance / 12.0) + (direction_changes * 0.7))
    movement = min(1.0, mean_motion / 18.0)
    smoothness = max(0.0, 1.0 - jitter)
    composition = _composition_stability(centers, frames[0].shape)
    usability = round((smoothness * 0.45) + (movement * 0.25) + (composition * 0.3), 6)
    movement_type = _movement_type(vectors, jitter, movement)
    return MotionAnalysis(
        smoothness_score=round(smoothness, 6),
        jitter_score=round(jitter, 6),
        movement_score=round(movement, 6),
        composition_score=round(composition, 6),
        usability_score=usability,
        movement_type=movement_type,
    )


def reject_bad_motion(result: MotionAnalysis, starts_near_clip_edge: bool) -> str | None:
    if starts_near_clip_edge and result.jitter_score >= 0.55:
        return "takeoff_or_landing_motion"
    if result.jitter_score >= 0.65:
        return "unstable_yaw_or_pan"
    if result.smoothness_score < 0.3:
        return "excessive_jitter"
    if result.movement_type == "searching":
        return "search_flight_before_subject"
    return None


def _bright_center(frame: np.ndarray) -> tuple[float, float]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
    height, width = gray.shape[:2]
    total = float(gray.sum())
    if total <= 0.0:
        return (width / 2.0, height / 2.0)
    rows, cols = np.indices((height, width))
    center_x = float((cols * gray).sum() / total)
    center_y = float((rows * gray).sum() / total)
    return (center_x, center_y)


def _direction_change_ratio(vectors: list[tuple[float, float]]) -> float:
    """Path inefficiency: how much the subject wanders instead of moving purposefully.

    1.0 means the motion fully cancels itself out (pure back-and-forth jitter);
    0.0 means a perfectly straight, purposeful move.
    """
    if not vectors:
        return 0.0
    path = float(sum(float(np.hypot(dx, dy)) for dx, dy in vectors))
    if path <= 0.0:
        return 0.0
    net_x = float(sum(dx for dx, _ in vectors))
    net_y = float(sum(dy for _, dy in vectors))
    net = float(np.hypot(net_x, net_y))
    return max(0.0, min(1.0, 1.0 - (net / path)))


def _composition_stability(centers: list[tuple[float, float]], shape: tuple[int, ...]) -> float:
    if len(centers) < 2:
        return 0.5
    height, width = shape[0], shape[1]
    xs = np.array([center[0] for center in centers], dtype=float)
    ys = np.array([center[1] for center in centers], dtype=float)
    x_spread = float(np.std(xs)) / max(1.0, float(width))
    y_spread = float(np.std(ys)) / max(1.0, float(height))
    return round(max(0.0, min(1.0, 1.0 - (x_spread + y_spread) * 2.0)), 6)


def _movement_type(vectors: list[tuple[float, float]], jitter: float, movement: float) -> str:
    if not vectors or movement < 0.08:
        return "hover"
    if jitter >= 0.55 and movement >= 0.45:
        return "searching"
    net_x = float(sum(dx for dx, _ in vectors))
    net_y = float(sum(dy for _, dy in vectors))
    if abs(net_x) >= abs(net_y) * 1.5:
        return "pan_right" if net_x >= 0 else "pan_left"
    if abs(net_y) >= abs(net_x) * 1.5:
        return "tilt_down" if net_y >= 0 else "tilt_up"
    return "push_in"
