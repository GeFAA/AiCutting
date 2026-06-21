from pathlib import Path

import cv2
import numpy as np

from aicutting.core.models import ClipCandidate, MediaAsset

WINDOW_DURATION_S = 5.0
WINDOW_STRIDE_S = 5.0
LONG_SHOT_HEAD_TRIM_S = 2.0
MIN_CANDIDATE_DURATION_S = 3.0
MAX_CANDIDATES_PER_ASSET = 60


def score_frame_quality(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    normalized = min(1.0, (sharpness / 500.0) * 0.6 + (contrast / 80.0) * 0.4)
    return round(normalized, 6)


def build_candidates_from_scenes(
    asset: MediaAsset,
    scenes: list[tuple[float, float]],
    quality_score: float,
    motion_score: float,
) -> list[ClipCandidate]:
    candidates: list[ClipCandidate] = []
    for start_s, end_s in scenes:
        for window_start_s, window_end_s in _candidate_windows(start_s, end_s):
            candidates.append(
                ClipCandidate(
                    asset_path=asset.path,
                    start_s=window_start_s,
                    end_s=window_end_s,
                    quality_score=quality_score,
                    motion_score=motion_score,
                    diversity_key=_diversity_key(asset.path, window_start_s),
                )
            )
    return candidates


def score_candidates_from_video(
    asset: MediaAsset,
    candidates: list[ClipCandidate],
) -> list[ClipCandidate]:
    if not candidates:
        return []

    capture = cv2.VideoCapture(str(asset.path))
    try:
        if not capture.isOpened():
            return candidates[:MAX_CANDIDATES_PER_ASSET]

        scored: list[ClipCandidate] = []
        for candidate in candidates:
            frames = [
                frame
                for time_s in _sample_times(candidate.start_s, candidate.end_s)
                if (frame := _read_frame_at(capture, time_s)) is not None
            ]
            if not frames:
                scored.append(candidate)
                continue
            quality = round(float(np.mean([score_frame_quality(frame) for frame in frames])), 6)
            motion = _score_motion(frames)
            scored.append(
                candidate.model_copy(
                    update={
                        "quality_score": quality,
                        "motion_score": motion,
                    }
                )
            )

        return sorted(scored, key=lambda item: item.composite_score, reverse=True)[
            :MAX_CANDIDATES_PER_ASSET
        ]
    finally:
        capture.release()


def _candidate_windows(start_s: float, end_s: float) -> list[tuple[float, float]]:
    duration_s = end_s - start_s
    if duration_s < 1.0:
        return []
    if duration_s <= WINDOW_DURATION_S:
        return [(round(start_s, 3), round(end_s, 3))]

    first_start = start_s
    if start_s <= 0.001 and duration_s >= WINDOW_DURATION_S + LONG_SHOT_HEAD_TRIM_S:
        first_start += LONG_SHOT_HEAD_TRIM_S

    windows: list[tuple[float, float]] = []
    cursor = first_start
    latest_start = end_s - MIN_CANDIDATE_DURATION_S
    while cursor <= latest_start:
        window_end = min(cursor + WINDOW_DURATION_S, end_s)
        if window_end - cursor >= MIN_CANDIDATE_DURATION_S:
            windows.append((round(cursor, 3), round(window_end, 3)))
        cursor += WINDOW_STRIDE_S
    return windows


def _sample_times(start_s: float, end_s: float) -> list[float]:
    duration_s = end_s - start_s
    if duration_s <= 1.0:
        return [round((start_s + end_s) / 2, 3)]
    return [
        round(start_s + min(0.75, duration_s * 0.2), 3),
        round((start_s + end_s) / 2, 3),
        round(end_s - min(0.75, duration_s * 0.2), 3),
    ]


def _read_frame_at(capture: cv2.VideoCapture, time_s: float) -> np.ndarray | None:
    capture.set(cv2.CAP_PROP_POS_MSEC, time_s * 1000.0)
    ok, frame = capture.read()
    if not ok or frame is None:
        return None
    height, width = frame.shape[:2]
    if width <= 640:
        return frame
    scale = 640 / width
    return cv2.resize(frame, (640, max(1, int(height * scale))), interpolation=cv2.INTER_AREA)


def _score_motion(frames: list[np.ndarray]) -> float:
    if len(frames) < 2:
        return 0.2
    diffs: list[float] = []
    for previous, current in zip(frames, frames[1:], strict=False):
        previous_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
        current_gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
        diff = float(np.mean(cv2.absdiff(previous_gray, current_gray))) / 50.0
        diffs.append(min(1.0, diff))
    return round(float(np.mean(diffs)), 6)


def _diversity_key(path: Path, start_s: float) -> str:
    bucket = int(start_s // 10)
    return f"{path.stem}:{bucket}"
