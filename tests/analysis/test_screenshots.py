from pathlib import Path

import cv2
import numpy as np
import pytest

from aicutting.analysis.screenshots import (
    build_contact_sheets,
    extract_location_keyframes,
    sample_footage_moments,
)
from aicutting.core.models import ClipCandidate, MediaAsset


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


def test_sample_skips_takeoff_and_landing_zones() -> None:
    asset = MediaAsset(path=Path("flight.mp4"), duration_s=60.0, width=1920, height=1080, fps=25.0)

    moments = sample_footage_moments([asset], trim_s=12.0, stride_s=4.0, max_moments=48)

    assert moments, "expected sampled moments"
    assert all(12.0 <= m.timestamp_s <= 48.0 for m in moments)
    assert len({m.moment_id for m in moments}) == len(moments)


def test_build_contact_sheets_tiles_moments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    asset = MediaAsset(
        path=tmp_path / "flight.mp4", duration_s=60.0, width=1920, height=1080, fps=25.0
    )
    (tmp_path / "flight.mp4").write_text("", encoding="utf-8")
    moments = sample_footage_moments([asset], trim_s=12.0, stride_s=8.0, max_moments=6)

    class FakeCapture:
        def isOpened(self) -> bool:
            return True

        def set(self, prop: int, value: float) -> None:
            del prop, value

        def read(self) -> tuple[bool, np.ndarray]:
            return True, np.full((1080, 1920, 3), 128, dtype=np.uint8)

        def release(self) -> None:
            pass

    monkeypatch.setattr(
        "aicutting.analysis.screenshots.cv2.VideoCapture", lambda _: FakeCapture()
    )

    sheets = build_contact_sheets(moments, tmp_path / "sheets", per_sheet=4, columns=2)

    assert sheets, "expected contact sheets"
    assert sheets[0].path.exists()
    covered = [mid for sheet in sheets for mid in sheet.moment_ids]
    assert covered == [m.moment_id for m in moments]
