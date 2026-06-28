"""Horizon levelling: detect a tilted horizon per clip and rotate it level.

Drone shots often sit a degree or two off level. This finds the dominant near-horizontal line in a
representative frame (Hough), and returns the counter-rotation that brings it back to horizontal --
but only for plausible tilts, so a misdetected steep "horizon" is left alone. The tilt-to-angle math
is pure; ``clip_level_degrees`` adds the cv2 detection and frame sampling.
"""

import math
from pathlib import Path
from statistics import median

import cv2
import numpy as np

from aicutting.core.models import TimelineClip

_MIN_DEG = 0.6  # below this the shot is level enough -- not worth the overscan crop
_MAX_DEG = 6.0  # above this it is probably a misdetection / deliberate diagonal -- leave it alone
_MAX_OFF = 15.0  # a line counts as the horizon only within this many degrees of horizontal


def dominant_horizontal_tilt(angles: list[float], max_off: float = _MAX_OFF) -> float | None:
    """Median tilt (deg from horizontal) of the near-horizontal lines, or None if there are none."""
    near = [angle for angle in angles if abs(angle) <= max_off]
    if not near:
        return None
    return round(median(near), 4)


def level_angle(tilt: float | None, min_deg: float = _MIN_DEG, max_deg: float = _MAX_DEG) -> float:
    """The correction that levels ``tilt``: ``-tilt`` for a plausible tilt, else 0.0 (no turn)."""
    if tilt is None or abs(tilt) < min_deg or abs(tilt) > max_deg:
        return 0.0
    return round(-tilt, 3)


def detect_horizon_tilt(frame: np.ndarray) -> float | None:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 180)
    lines = cv2.HoughLines(edges, 1, math.pi / 180.0, threshold=140)
    if lines is None:
        return None
    angles: list[float] = []
    for line in lines[:80]:
        theta_deg = math.degrees(float(line[0][1]))
        # Hough theta is the angle of the line's normal; a horizontal line has theta = 90 deg, so
        # (theta - 90) is how far the line tilts from horizontal.
        angles.append(theta_deg - 90.0)
    return dominant_horizontal_tilt(angles)


def clip_level_degrees(clips: list[TimelineClip]) -> list[float]:
    """Per-clip level correction in degrees (0.0 where no clear horizon is found or unreadable)."""
    corrections: list[float] = [0.0] * len(clips)
    by_asset: dict[Path, list[int]] = {}
    for index, clip in enumerate(clips):
        by_asset.setdefault(clip.asset_path, []).append(index)
    for asset_path, indices in by_asset.items():
        capture = cv2.VideoCapture(str(asset_path))
        try:
            for index in indices:
                clip = clips[index]
                mid_s = (clip.source_start_s + clip.source_end_s) / 2.0
                capture.set(cv2.CAP_PROP_POS_MSEC, mid_s * 1000.0)
                ok, frame = capture.read()
                if ok and frame is not None:
                    corrections[index] = level_angle(detect_horizon_tilt(frame))
        finally:
            capture.release()
    return corrections
