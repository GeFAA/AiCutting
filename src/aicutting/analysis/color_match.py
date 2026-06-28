"""Cross-clip colour matching: nudge every clip toward one shared look.

Clips shot at different times or in different light drift apart in exposure and tint. This computes
a subtle per-channel gain that pulls each clip's average colour toward the median across the cut, so
the finished film reads as one consistent grade. ``compute_color_gains`` is pure (testable without
decoding video); ``match_clip_color_gains`` adds the cv2 frame sampling.
"""

from pathlib import Path
from statistics import median

import cv2
import numpy as np

from aicutting.core.models import TimelineClip

RGBMean = tuple[float, float, float]
RGBGain = tuple[float, float, float]

_UNIT: RGBGain = (1.0, 1.0, 1.0)
# A subtle, clamped match: blend halfway to the reference and never gain/cut a channel hard, so the
# film harmonises without flattening intentional differences between shots.
_DEFAULT_STRENGTH = 0.5
_DEFAULT_CLAMP = (0.85, 1.18)


def compute_color_gains(
    means: list[RGBMean | None],
    strength: float = _DEFAULT_STRENGTH,
    clamp: tuple[float, float] = _DEFAULT_CLAMP,
) -> list[RGBGain]:
    """Per-clip RGB gains pulling each clip's mean colour toward the median, clamped and subtle.

    ``means`` holds one (R, G, B) average per clip (``None`` where a clip could not be read). Any
    clip that is unreadable -- or every clip when fewer than two are readable -- gets a unit gain.
    """
    valid = [m for m in means if m is not None]
    if len(valid) < 2:
        return [_UNIT for _ in means]
    reference = tuple(median(m[channel] for m in valid) for channel in range(3))
    low, high = clamp
    gains: list[RGBGain] = []
    for mean in means:
        if mean is None or any(value <= 0 for value in mean):
            gains.append(_UNIT)
            continue
        corrected = []
        for channel in range(3):
            raw = 1.0 + strength * (reference[channel] / mean[channel] - 1.0)
            corrected.append(round(min(max(raw, low), high), 4))
        gains.append((corrected[0], corrected[1], corrected[2]))
    return gains


def match_clip_color_gains(clips: list[TimelineClip]) -> list[RGBGain]:
    """Sample one frame per clip and return the per-clip colour-match gains (best-effort)."""
    means = _clip_means(clips)
    return compute_color_gains(means)


def _clip_means(clips: list[TimelineClip]) -> list[RGBMean | None]:
    # Group by source file so each video is opened once; sample a frame from the middle of the
    # clip's source window. Anything unreadable becomes None (handled as a unit gain downstream).
    means: list[RGBMean | None] = [None] * len(clips)
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
                    means[index] = _frame_mean(frame)
        finally:
            capture.release()
    return means


def _frame_mean(frame: np.ndarray) -> RGBMean:
    small = cv2.resize(frame, (160, 90))  # cv2 is BGR
    blue, green, red = (float(small[:, :, channel].mean()) for channel in range(3))
    return (red, green, blue)
