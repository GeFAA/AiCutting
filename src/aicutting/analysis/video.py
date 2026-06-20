from pathlib import Path

import cv2
import numpy as np

from aicutting.core.models import ClipCandidate, MediaAsset


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
        if end_s - start_s < 1.0:
            continue
        candidates.append(
            ClipCandidate(
                asset_path=asset.path,
                start_s=start_s,
                end_s=end_s,
                quality_score=quality_score,
                motion_score=motion_score,
                diversity_key=_diversity_key(asset.path, start_s),
            )
        )
    return candidates


def _diversity_key(path: Path, start_s: float) -> str:
    bucket = int(start_s // 10)
    return f"{path.stem}:{bucket}"
