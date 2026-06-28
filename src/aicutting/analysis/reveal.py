"""Land reveal cuts on their payoff instead of chopping mid-move.

A drone *reveal* (a tilt-up or rise that uncovers a vista) builds for a few seconds and then
**settles** on the revealed view -- and that settled view is the payoff. When the moment the agent
rated sits in the *build-up*, the centred cut window ends while the camera is still moving and the
reveal is chopped off before it pays off (you never see the vista).

This finds that case from the source motion: if a cut **ends while the camera is still clearly
moving** and the motion **settles** a little further on (a sustained drop), the window is slid
forward -- keeping its exact duration, so the beat grid is untouched -- to land on the settle. The
settle detection (:func:`landing_shift`) is pure; :func:`clip_landing_shifts` adds the motion
sampling and clamps the slide to the file's safe zone.
"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from aicutting.core.models import TimelineClip

_DT = 0.5  # motion sampling interval (s) -- coarse is plenty to see a settle
_MAX_SHIFT_S = 5.0  # never chase a payoff further than this many seconds ahead
_TRIM_S = 12.0  # keep the slid window out of the very start / end of the file
_PROXY_W = 128  # decode the motion proxy at this width -- tiny, just the global motion magnitude
_PROXY_H = 72
_SEEK_PAD_S = 1.0  # fast-seek this far before the region, then accurate-skip to align exactly
_FF_THREADS = 2  # threads per ffmpeg proxy decode (kept low so the pool can run several at once)


def landing_shift(
    motion: list[float],
    dt: float,
    end_idx: int,
    *,
    max_shift_s: float = _MAX_SHIFT_S,
    drop_ratio: float = 0.6,
    settle_run: int = 3,
    hold_s: float = 0.3,
    move_min: float = 8.0,
) -> float:
    """Seconds to slide a window forward so it lands on the reveal's settle (0.0 = leave it).

    ``motion[i]`` is the camera-motion magnitude sampled every ``dt`` seconds; ``end_idx`` is the
    index where the cut currently ends. The slide fires only on a genuine chopped reveal:

    * the camera must be **clearly and steadily moving into the cut** -- both the cut sample and the
      one before it at least ``move_min`` -- so a near-static shot, or one already easing off, is
      left alone; and
    * the motion must then **settle**: drop to ``drop_ratio`` of that moving level for at least
      ``settle_run`` consecutive samples (the camera coming to rest on the revealed view).

    When both hold, the window slides so it ends ``hold_s`` past the settle, bounded by
    ``max_shift_s``. A cut with no clear settle within reach is left where it is -- the conservative
    default, so this never drags a good cut off its content.
    """
    n = len(motion)
    if dt <= 0 or end_idx < 1 or end_idx >= n - settle_run:
        return 0.0
    moving = min(motion[end_idx - 1], motion[end_idx])
    if moving < move_min:
        return 0.0
    threshold = moving * drop_ratio
    max_idx = min(n, end_idx + int(max_shift_s / dt) + 1)
    for i in range(end_idx + 1, max_idx - settle_run + 1):
        if all(motion[j] <= threshold for j in range(i, i + settle_run)):
            return round(min((i - end_idx) * dt + hold_s, max_shift_s), 3)
    return 0.0


def clip_landing_shifts(
    clips: list[TimelineClip],
    *,
    dt: float = _DT,
    max_shift_s: float = _MAX_SHIFT_S,
    trim_s: float = _TRIM_S,
) -> list[float]:
    """Per-clip forward slide in seconds (0.0 where the cut already lands well or is unreadable).

    Mirrors :func:`aicutting.analysis.horizon.clip_level_degrees`: groups clips by file (reading
    each file's duration once), samples a short motion proxy around each cut's end, and asks
    :func:`landing_shift` whether the cut chops a reveal. Any slide is clamped so the shifted window
    stays inside the file's safe zone, so the duration is preserved and the beat grid intact.
    """
    shifts: list[float] = [0.0] * len(clips)
    if not clips:
        return shifts
    durations = {path: _duration_s(path) for path in {clip.asset_path for clip in clips}}
    # Each clip's proxy decode is an independent ffmpeg subprocess (GIL released while it runs), so
    # a small thread pool overlaps them. ffmpeg threads are capped so the pool stays within cores.
    workers = max(1, min(6, (os.cpu_count() or 4) // _FF_THREADS, len(clips)))

    def shift_for(index: int) -> tuple[int, float]:
        clip = clips[index]
        return index, _clip_shift(
            clip.asset_path, clip, durations[clip.asset_path], dt, max_shift_s, trim_s
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for index, shift in pool.map(shift_for, range(len(clips))):
            shifts[index] = shift
    return shifts


def _clip_shift(
    asset_path: Path,
    clip: TimelineClip,
    file_duration: float,
    dt: float,
    max_shift_s: float,
    trim_s: float,
) -> float:
    need = clip.source_end_s - clip.source_start_s
    if need <= 0 or dt <= 0:
        return 0.0
    # Settle detection only reads the motion at the cut end and forward, so sample just the tail
    # region (a couple samples of pre-context + the lookahead) -- a fixed, small decode no matter
    # how long the clip is, instead of decoding the whole clip.
    pre = 2
    low = max(0.0, clip.source_end_s - pre * dt)
    span = clip.source_end_s + max_shift_s + dt - low
    profile = _motion_profile(asset_path, low, span, dt)
    if len(profile) < 3:
        return 0.0
    end_idx = round((clip.source_end_s - low) / dt)
    shift = landing_shift(profile, dt, end_idx, max_shift_s=max_shift_s)
    if shift <= 0.0:
        return 0.0
    # Keep the slid window inside the file's safe zone (never past the trimmed tail).
    safe_high = max(0.0, file_duration - min(trim_s, file_duration * 0.1))
    allowed = max(0.0, safe_high - clip.source_end_s)
    return round(min(shift, allowed), 3)


def _motion_profile(asset_path: Path, low: float, span: float, dt: float) -> list[float]:
    # motion[i] is the frame-to-frame motion magnitude at time low + i*dt. ffmpeg decodes the short
    # tail region downscaled to a tiny gray proxy in one pass (a fast keyframe seek to low - pad,
    # then an accurate skip of pad so the first output frame lands exactly on `low`), far cheaper
    # than re-decoding full 4K frames through OpenCV. Any failure returns [] -> the caller keeps the
    # cut as-is.
    if span <= 0 or dt <= 0:
        return []
    pad = min(_SEEK_PAD_S, low)
    command = [
        "ffmpeg", "-v", "error", "-nostdin", "-threads", str(_FF_THREADS),
        "-ss", f"{low - pad:.3f}", "-i", asset_path.as_posix(),
        "-ss", f"{pad:.3f}", "-t", f"{span:.3f}",
        "-vf", f"scale={_PROXY_W}:{_PROXY_H},fps={1.0 / dt:g}",
        "-pix_fmt", "gray", "-f", "rawvideo", "-",
    ]
    try:
        result = subprocess.run(command, capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    frame_size = _PROXY_W * _PROXY_H
    count = len(result.stdout) // frame_size
    if count < 3:
        return []
    frames = np.frombuffer(result.stdout, dtype=np.uint8, count=count * frame_size)
    frames = frames.reshape(count, _PROXY_H, _PROXY_W).astype(np.float32)
    diffs = np.mean(np.abs(np.diff(frames, axis=0)), axis=(1, 2))
    # profile[0] mirrors profile[1] (first frame has no predecessor); profile[i>=1] = diffs[i-1].
    return [float(diffs[0]), *(float(d) for d in diffs)]


def _duration_s(asset_path: Path) -> float:
    capture = cv2.VideoCapture(str(asset_path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
        frames = capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    finally:
        capture.release()
    if fps > 0.0 and frames > 0.0:
        return frames / fps
    return 0.0
