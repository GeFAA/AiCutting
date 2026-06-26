from pathlib import Path

import cv2
import numpy as np
import pytest

from aicutting.analysis.screenshots import extract_location_keyframes
from aicutting.core.models import ClipCandidate


def _write_tiny_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        5.0,
        (64, 48),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV cannot write MJPG test videos in this environment")

    for index in range(10):
        frame = np.full((48, 64, 3), index * 20, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_extract_location_keyframes_writes_midpoint_jpegs(tmp_path: Path) -> None:
    video = tmp_path / "clip.avi"
    _write_tiny_video(video)
    candidate = ClipCandidate(
        asset_path=video,
        start_s=0.2,
        end_s=1.4,
        quality_score=0.9,
        motion_score=0.8,
        diversity_key="clip:0",
    )

    images = extract_location_keyframes([candidate], tmp_path / "location-screenshots")

    assert len(images) == 1
    assert images[0].suffix == ".jpg"
    assert images[0].exists()
    assert cv2.imread(str(images[0])) is not None


def test_extract_location_keyframes_skips_missing_assets(tmp_path: Path) -> None:
    candidate = ClipCandidate(
        asset_path=tmp_path / "missing.mp4",
        start_s=0.0,
        end_s=2.0,
        quality_score=0.9,
        motion_score=0.8,
        diversity_key="missing:0",
    )

    images = extract_location_keyframes([candidate], tmp_path / "location-screenshots")

    assert images == []
