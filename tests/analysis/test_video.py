from pathlib import Path

import numpy as np

from aicutting.analysis.video import build_candidates_from_scenes, score_frame_quality
from aicutting.core.models import MediaAsset


def test_score_frame_quality_rewards_contrast() -> None:
    flat = np.full((20, 20, 3), 120, dtype=np.uint8)
    contrast = np.zeros((20, 20, 3), dtype=np.uint8)
    contrast[:, 10:] = 255

    assert score_frame_quality(contrast) > score_frame_quality(flat)


def test_build_candidates_from_scenes_skips_tiny_segments() -> None:
    asset = MediaAsset(path=Path("clip.mp4"), duration_s=20.0, width=1920, height=1080, fps=25.0)
    candidates = build_candidates_from_scenes(
        asset,
        scenes=[(0.0, 0.5), (1.0, 5.0)],
        quality_score=0.7,
        motion_score=0.4,
    )

    assert len(candidates) == 1
    assert candidates[0].start_s == 1.0
