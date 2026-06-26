import numpy as np

from aicutting.analysis.drone_shots import analyze_drone_shot_frames
from aicutting.core.models import DroneShotType


def _frame(center_x: int, center_y: int, size: int = 96) -> np.ndarray:
    frame = np.zeros((size, size, 3), dtype=np.uint8)
    frame[max(0, center_y - 8) : center_y + 8, max(0, center_x - 8) : center_x + 8] = 255
    return frame


def test_classifies_smooth_reveal_with_high_director_score() -> None:
    frames = [_frame(18, 48), _frame(34, 48), _frame(52, 48), _frame(70, 48)]

    result = analyze_drone_shot_frames(frames, starts_near_clip_edge=False)

    assert result.shot_type == DroneShotType.REVEAL
    assert result.rejection_reason is None
    assert result.drone_director_score >= 0.7
    assert "smooth" in " ".join(result.reasons)


def test_rejects_search_motion_with_direction_changes() -> None:
    frames = [_frame(18, 48), _frame(74, 48), _frame(24, 48), _frame(72, 48)]

    result = analyze_drone_shot_frames(frames, starts_near_clip_edge=False)

    assert result.shot_type == DroneShotType.SEARCH_MOTION
    assert result.rejection_reason == "search_flight_before_subject"
    assert result.drone_director_score < 0.5


def test_rejects_jitter_near_edges_as_takeoff_or_landing() -> None:
    frames = [_frame(48, 10), _frame(20, 72), _frame(70, 18), _frame(30, 80)]

    result = analyze_drone_shot_frames(frames, starts_near_clip_edge=True)

    assert result.shot_type == DroneShotType.TAKEOFF_OR_LANDING
    assert result.rejection_reason == "takeoff_or_landing_motion"
