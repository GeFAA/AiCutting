from aicutting.analysis.color_match import compute_color_gains


def test_pulls_colour_outliers_toward_the_reference() -> None:
    # Three clips that differ only in red; the median red is the middle clip's 150.
    means = [(200.0, 120.0, 120.0), (150.0, 120.0, 120.0), (100.0, 120.0, 120.0)]
    gains = compute_color_gains(means, strength=0.5, clamp=(0.7, 1.4))

    assert gains[0][0] < 1.0  # too red -> pulled down
    assert gains[2][0] > 1.0  # too dark-red -> pulled up
    assert gains[1] == (1.0, 1.0, 1.0)  # the reference clip is untouched
    assert gains[0][1] == 1.0 and gains[0][2] == 1.0  # green/blue already match -> no change


def test_clamps_extreme_corrections_so_the_match_stays_subtle() -> None:
    means = [(255.0, 10.0, 10.0), (10.0, 10.0, 10.0)]
    gains = compute_color_gains(means, strength=1.0, clamp=(0.85, 1.18))

    assert all(0.85 <= channel <= 1.18 for clip in gains for channel in clip)


def test_strength_scales_the_correction() -> None:
    means = [(200.0, 100.0, 100.0), (100.0, 100.0, 100.0)]  # ref red = 150
    gentle = compute_color_gains(means, strength=0.25, clamp=(0.1, 3.0))
    strong = compute_color_gains(means, strength=1.0, clamp=(0.1, 3.0))
    # the stronger correction moves the red gain further from 1.0
    assert abs(strong[0][0] - 1.0) > abs(gentle[0][0] - 1.0)


def test_unit_gains_when_too_few_clips_to_match() -> None:
    assert compute_color_gains([(100.0, 100.0, 100.0)]) == [(1.0, 1.0, 1.0)]
    # only one readable clip -> nothing to match against
    assert compute_color_gains([(100.0, 100.0, 100.0), None]) == [(1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]


def test_unreadable_clips_get_unit_gains() -> None:
    means = [(200.0, 120.0, 120.0), (150.0, 120.0, 120.0), None, (100.0, 120.0, 120.0)]
    gains = compute_color_gains(means)
    assert gains[2] == (1.0, 1.0, 1.0)
    assert len(gains) == len(means)
