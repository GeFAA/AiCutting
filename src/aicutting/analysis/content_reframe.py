"""Content-aware reframe: shift the vertical/square crop toward the subject.

A landscape source cover-cropped to 9:16 / 1:1 loses most of its width. Instead of always cropping
the dead centre, this finds the most detailed band of columns (where the subject / structure sits)
and returns the horizontal crop offset that keeps it -- defaulting to centre when nothing clearly
stands out, so the default reframe is unchanged. ``best_window_offset`` is pure; the per-clip
``clip_crop_offsets`` adds the cv2 frame sampling.
"""

from pathlib import Path

import cv2
import numpy as np

from aicutting.core.models import Timeline, TimelineClip

# Only move the crop when the best band is at least this much more interesting than the centre band,
# so a marginal difference keeps the (byte-identical) centre crop.
_MARGIN = 1.08


def best_window_offset(scores: list[float], window_cols: int, margin: float = _MARGIN) -> float:
    """Horizontal crop offset in [0, 1] for the most interesting window; 0.5 (centre) if none wins.

    ``scores`` is a per-column interest measure and ``window_cols`` is the crop width in columns.
    Returns the chosen window's left edge as a fraction of the available travel (0 = hard left,
    1 = hard right), or 0.5 when the best window is not clearly better than the centre one.
    """
    n = len(scores)
    if window_cols <= 0 or window_cols >= n:
        return 0.5
    window_sum = sum(scores[:window_cols])
    best_sum, best_left = window_sum, 0
    for left in range(1, n - window_cols + 1):
        window_sum += scores[left + window_cols - 1] - scores[left - 1]
        if window_sum > best_sum:
            best_sum, best_left = window_sum, left
    centre_left = (n - window_cols) // 2
    centre_sum = sum(scores[centre_left : centre_left + window_cols])
    if best_sum <= centre_sum * margin:
        return 0.5
    return round(best_left / (n - window_cols), 4)


def clip_crop_offsets(clips: list[TimelineClip], timeline: Timeline) -> list[float]:
    """Per-clip horizontal crop offset for a portrait/square master (0.5 where it can't be read)."""
    target_aspect = timeline.width / timeline.height
    offsets: list[float] = [0.5] * len(clips)
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
                    offsets[index] = _frame_offset(frame, target_aspect)
        finally:
            capture.release()
    return offsets


def _frame_offset(frame: np.ndarray, target_aspect: float) -> float:
    source_aspect = frame.shape[1] / frame.shape[0]
    window_frac = target_aspect / source_aspect  # share of the width the crop keeps
    if window_frac >= 1.0:  # target is not narrower than the source -> no horizontal crop
        return 0.5
    small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (192, 108))
    scores = small.std(axis=0).astype(float).tolist()  # per-column detail (vertical structure)
    return best_window_offset(scores, max(1, round(len(scores) * window_frac)))
