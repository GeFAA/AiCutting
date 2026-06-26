import numpy as np

from aicutting.analysis.motion import analyze_motion_frames, reject_bad_motion


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
