from pathlib import Path

import numpy as np
import pytest

from aicutting.analysis.motion import (
    analyze_motion_frames,
    reject_bad_motion,
    score_moment_motion,
    select_usable_moments,
)
from aicutting.director.edit_models import FootageMoment


def _frame(x_offset: int = 0, y_offset: int = 0) -> np.ndarray:
    frame = np.zeros((80, 120, 3), dtype=np.uint8)
    frame[25 + y_offset : 55 + y_offset, 35 + x_offset : 85 + x_offset] = 255
    return frame


def test_smooth_motion_scores_better_than_jittery_motion() -> None:
    smooth = [_frame(index * 2, 0) for index in range(5)]
    jittery = [_frame(offset, 0) for offset in [0, 8, -5, 11, -3]]

    smooth_result = analyze_motion_frames(smooth)
    jitter_result = analyze_motion_frames(jittery)

    assert smooth_result.smoothness_score > jitter_result.smoothness_score
    assert jitter_result.jitter_score > smooth_result.jitter_score


def test_abrupt_direction_change_is_rejected_as_unstable_yaw() -> None:
    frames = [_frame(offset, 0) for offset in [0, 12, 24, 6, -8]]

    result = analyze_motion_frames(frames)
    rejection = reject_bad_motion(result, starts_near_clip_edge=False)

    assert rejection == "unstable_yaw_or_pan"


def test_edge_shaky_motion_is_rejected_as_takeoff_or_landing() -> None:
    frames = [_frame(offset, offset // 2) for offset in [0, 18, -12, 22, -8]]

    result = analyze_motion_frames(frames)
    rejection = reject_bad_motion(result, starts_near_clip_edge=True)

    assert rejection == "takeoff_or_landing_motion"


class _BurstCapture:
    """A fake cv2.VideoCapture that yields a known motion profile, frame by frame."""

    def __init__(self, offsets: list[int]) -> None:
        self._offsets = offsets
        self._reads = 0

    def isOpened(self) -> bool:
        return True

    def set(self, prop: int, value: float) -> None:
        del prop, value

    def read(self) -> tuple[bool, np.ndarray]:
        offset = self._offsets[self._reads % len(self._offsets)]
        self._reads += 1
        frame = np.zeros((80, 120, 3), dtype=np.uint8)
        frame[25:55, 45 + offset : 75 + offset] = 255
        return True, frame

    def release(self) -> None:
        pass


def test_score_moment_motion_scores_each_moment_per_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smooth = Path("smooth.mp4")
    shaky = Path("shaky.mp4")
    captures = {
        smooth: _BurstCapture([0, 3, 6, 9, 12]),
        shaky: _BurstCapture([0, 16, -12, 20, -8]),
    }
    monkeypatch.setattr(
        "aicutting.analysis.motion.cv2.VideoCapture",
        lambda path: captures[Path(path)],
    )
    moments = [
        FootageMoment(moment_id="smooth", asset_path=smooth, timestamp_s=10.0),
        FootageMoment(moment_id="shaky", asset_path=shaky, timestamp_s=10.0),
    ]

    scores = score_moment_motion(moments)

    assert set(scores) == {"smooth", "shaky"}
    assert scores["smooth"].smoothness_score > scores["shaky"].smoothness_score
    assert reject_bad_motion(scores["shaky"], starts_near_clip_edge=False) is not None


def test_score_moment_motion_omits_unreadable_files(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ClosedCapture:
        def isOpened(self) -> bool:
            return False

        def release(self) -> None:
            pass

    monkeypatch.setattr(
        "aicutting.analysis.motion.cv2.VideoCapture", lambda _path: _ClosedCapture()
    )
    moments = [FootageMoment(moment_id="m1", asset_path=Path("missing.mp4"), timestamp_s=5.0)]

    assert score_moment_motion(moments) == {}


def test_select_usable_moments_drops_jittery_keeps_stable() -> None:
    stable = analyze_motion_frames([_frame(index * 3, 0) for index in range(5)])
    jittery = analyze_motion_frames([_frame(offset, 0) for offset in [0, 16, -10, 22, -6]])
    moments = [
        FootageMoment(moment_id=f"s{i}", asset_path=Path("a.mp4"), timestamp_s=float(i))
        for i in range(5)
    ]
    moments.append(FootageMoment(moment_id="jit", asset_path=Path("a.mp4"), timestamp_s=99.0))
    scores = {moment.moment_id: stable for moment in moments[:5]}
    scores["jit"] = jittery

    kept = {moment.moment_id for moment in select_usable_moments(moments, scores)}

    assert "jit" not in kept
    assert all(f"s{i}" in kept for i in range(5))


def test_select_usable_moments_keeps_moments_without_a_score() -> None:
    stable = analyze_motion_frames([_frame(index * 3, 0) for index in range(5)])
    jittery = analyze_motion_frames([_frame(offset, 0) for offset in [0, 16, -10, 22, -6]])
    moments = [
        FootageMoment(moment_id="s0", asset_path=Path("a.mp4"), timestamp_s=1.0),
        FootageMoment(moment_id="s1", asset_path=Path("a.mp4"), timestamp_s=2.0),
        FootageMoment(moment_id="s2", asset_path=Path("a.mp4"), timestamp_s=3.0),
        FootageMoment(moment_id="jit", asset_path=Path("a.mp4"), timestamp_s=4.0),
        FootageMoment(moment_id="unscored", asset_path=Path("a.mp4"), timestamp_s=5.0),
    ]
    scores = {"s0": stable, "s1": stable, "s2": stable, "jit": jittery}

    kept = {moment.moment_id for moment in select_usable_moments(moments, scores)}

    assert "unscored" in kept  # no score => keep
    assert "jit" not in kept


def test_select_usable_moments_caps_drop_rate_to_avoid_starvation() -> None:
    jittery = analyze_motion_frames([_frame(offset, 0) for offset in [0, 16, -10, 22, -6]])
    moments = [
        FootageMoment(moment_id=f"j{i}", asset_path=Path("a.mp4"), timestamp_s=float(i))
        for i in range(10)
    ]
    scores = {moment.moment_id: jittery for moment in moments}  # every moment looks unusable

    kept = select_usable_moments(moments, scores)

    # At most ~40% may be dropped, so at least 60% survive even when everything is flagged.
    assert len(kept) >= 6
