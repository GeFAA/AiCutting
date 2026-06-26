from pathlib import Path

import numpy as np
import pytest

from aicutting.analysis.video import (
    build_candidates_from_scenes,
    score_candidates_from_video,
    score_frame_quality,
)
from aicutting.core.models import ClipCandidate, DroneShotType, MediaAsset


def test_score_frame_quality_rewards_contrast() -> None:
    flat = np.full((20, 20, 3), 120, dtype=np.uint8)
    contrast = np.zeros((20, 20, 3), dtype=np.uint8)
    contrast[:, 10:] = 255

    assert score_frame_quality(contrast) > score_frame_quality(flat)


def test_score_frame_quality_rewards_sharp_edges() -> None:
    flat = np.full((20, 20, 3), 120, dtype=np.uint8)
    edged = np.zeros((20, 20, 3), dtype=np.uint8)
    edged[::2, :] = 255

    assert score_frame_quality(edged) > score_frame_quality(flat)


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


def test_build_candidates_from_scenes_splits_long_drone_shots() -> None:
    asset = MediaAsset(path=Path("clip.mp4"), duration_s=60.0, width=3840, height=2160, fps=60.0)

    candidates = build_candidates_from_scenes(
        asset,
        scenes=[(0.0, 60.0)],
        quality_score=0.7,
        motion_score=0.4,
    )

    assert len(candidates) >= 8
    assert candidates[0].start_s > 0.0
    assert any(candidate.start_s >= 24.0 for candidate in candidates)
    assert all(3.0 <= candidate.duration_s <= 6.0 for candidate in candidates)


def test_score_candidates_from_video_attaches_drone_director_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    video = tmp_path / "clip.mp4"
    video.write_text("", encoding="utf-8")
    asset = MediaAsset(path=video, duration_s=10.0, width=1920, height=1080, fps=25.0)
    candidate = ClipCandidate(
        asset_path=video,
        start_s=2.0,
        end_s=7.0,
        quality_score=0.5,
        motion_score=0.5,
        diversity_key="clip:0",
    )

    class FakeCapture:
        def isOpened(self) -> bool:
            return True

        def set(self, prop: int, value: float) -> None:
            del prop, value

        def read(self) -> tuple[bool, np.ndarray]:
            frame = np.zeros((96, 96, 3), dtype=np.uint8)
            frame[:, 40:60] = 255
            return True, frame

        def release(self) -> None:
            pass

    monkeypatch.setattr("aicutting.analysis.video.cv2.VideoCapture", lambda _: FakeCapture())

    scored = score_candidates_from_video(asset, [candidate])

    assert scored[0].shot_type != DroneShotType.UNKNOWN
    assert scored[0].drone_director_score is not None
