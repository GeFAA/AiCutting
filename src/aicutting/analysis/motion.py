from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from aicutting.director.edit_models import FootageMoment


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


def score_moment_motion(
    moments: Sequence[FootageMoment],
    span_s: float = 1.2,
    samples: int = 5,
    downscale_width: int = 320,
) -> dict[str, MotionAnalysis]:
    """Score the local camera motion around each sampled moment.

    For every moment a short burst of ``samples`` frames spanning ``span_s`` seconds and
    centred on its timestamp is read, downscaled for speed, and passed to
    :func:`analyze_motion_frames`. Moments are grouped by file so each video is opened
    once. Moments whose frames cannot be read are omitted, so the caller treats a missing
    score as "keep".
    """
    by_asset: dict[Path, list[FootageMoment]] = {}
    for moment in moments:
        by_asset.setdefault(moment.asset_path, []).append(moment)
    scores: dict[str, MotionAnalysis] = {}
    for asset_path, items in by_asset.items():
        capture = cv2.VideoCapture(str(asset_path))
        try:
            if not capture.isOpened():
                continue
            for moment in items:
                frames = _read_motion_burst(
                    capture, moment.timestamp_s, span_s, samples, downscale_width
                )
                if len(frames) >= 2:
                    scores[moment.moment_id] = analyze_motion_frames(frames)
        finally:
            capture.release()
    return scores


def select_usable_moments(
    moments: Sequence[FootageMoment],
    scores: Mapping[str, MotionAnalysis],
    min_usability: float = 0.3,
    max_drop_ratio: float = 0.4,
) -> list[FootageMoment]:
    """Drop the clearly-unusable moments without ever starving selection.

    A moment is a drop candidate when :func:`reject_bad_motion` flags its motion
    (shaky / searching / takeoff) or its ``usability_score`` falls below ``min_usability``.
    Moments without a motion score are always kept. At most ``max_drop_ratio`` of the
    moments are dropped: when more qualify, only the least-usable are removed up to that
    cap, so the most-usable bad moments survive rather than leaving selection empty.
    """
    candidates = [
        moment
        for moment in moments
        if moment.moment_id in scores
        and _is_unusable(scores[moment.moment_id], min_usability)
    ]
    if not candidates:
        return list(moments)
    max_drops = int(len(moments) * max_drop_ratio)
    if max_drops <= 0:
        return list(moments)
    candidates.sort(key=lambda moment: scores[moment.moment_id].usability_score)
    dropped = {moment.moment_id for moment in candidates[:max_drops]}
    return [moment for moment in moments if moment.moment_id not in dropped]


def _is_unusable(analysis: MotionAnalysis, min_usability: float) -> bool:
    if reject_bad_motion(analysis, starts_near_clip_edge=False) is not None:
        return True
    return analysis.usability_score < min_usability


def _read_motion_burst(
    capture: cv2.VideoCapture,
    timestamp_s: float,
    span_s: float,
    samples: int,
    downscale_width: int,
) -> list[np.ndarray]:
    half = max(0.0, span_s) / 2.0
    count = max(2, samples)
    frames: list[np.ndarray] = []
    for offset in np.linspace(-half, half, count):
        position_s = max(0.0, timestamp_s + float(offset))
        capture.set(cv2.CAP_PROP_POS_MSEC, position_s * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            continue
        frames.append(_downscale(frame, downscale_width))
    return frames


def _downscale(frame: np.ndarray, target_width: int) -> np.ndarray:
    width = frame.shape[1]
    if target_width <= 0 or width <= target_width:
        return frame
    scale = target_width / float(width)
    height = max(1, int(round(frame.shape[0] * scale)))
    return cv2.resize(frame, (target_width, height), interpolation=cv2.INTER_AREA)


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
