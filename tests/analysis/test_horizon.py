from aicutting.analysis.horizon import dominant_horizontal_tilt, level_angle


def test_dominant_tilt_is_the_median_of_near_horizontal_lines() -> None:
    # 40 deg is a diagonal, not the horizon -> excluded; the rest cluster around ~2.5 deg.
    angles = [2.0, 3.0, 2.5, 40.0, -1.0]
    assert dominant_horizontal_tilt(angles) == 2.25


def test_dominant_tilt_is_none_without_horizontal_lines() -> None:
    assert dominant_horizontal_tilt([55.0, -60.0, 80.0]) is None
    assert dominant_horizontal_tilt([]) is None


def test_level_angle_opposes_a_meaningful_tilt() -> None:
    # a 3 deg clockwise tilt is corrected by a 3 deg counter-rotation
    assert level_angle(3.0) == -3.0
    assert level_angle(-2.5) == 2.5


def test_level_angle_ignores_tiny_tilts() -> None:
    # below ~0.6 deg the shot is already level -- don't rotate (and pay the overscan crop) for noise
    assert level_angle(0.3) == 0.0


def test_level_angle_ignores_implausibly_large_tilts() -> None:
    # a 12 deg "horizon" is probably a misdetection or a deliberate diagonal -> leave it alone
    assert level_angle(12.0) == 0.0
    assert level_angle(None) == 0.0
