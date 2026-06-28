from aicutting.analysis.content_reframe import best_window_offset


def test_offset_follows_a_strong_right_side_subject() -> None:
    scores = [1.0] * 14 + [10.0] * 6  # all the detail is on the right
    assert best_window_offset(scores, window_cols=6) == 1.0


def test_offset_follows_a_strong_left_side_subject() -> None:
    scores = [10.0] * 6 + [1.0] * 14
    assert best_window_offset(scores, window_cols=6) == 0.0


def test_flat_interest_stays_centred() -> None:
    # nothing stands out -> keep the centre crop (so the default reframe is unchanged)
    assert best_window_offset([5.0] * 20, window_cols=6) == 0.5


def test_a_mild_bias_below_the_margin_stays_centred() -> None:
    # a slightly-more-interesting edge that is not clearly better than centre is ignored
    scores = [5.0] * 17 + [5.4, 5.4, 5.4]
    assert best_window_offset(scores, window_cols=6) == 0.5


def test_degenerate_windows_stay_centred() -> None:
    assert best_window_offset([1.0, 2.0, 3.0], window_cols=5) == 0.5  # window wider than the frame
    assert best_window_offset([], window_cols=3) == 0.5
