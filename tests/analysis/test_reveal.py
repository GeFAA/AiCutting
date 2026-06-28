from aicutting.analysis.reveal import landing_shift


def test_shifts_to_land_on_a_clear_settle() -> None:
    # strong, steady motion into the cut (end_idx=5), then a clear sustained settle: the window
    # should slide forward to land just after the settle.
    motion = [22.0, 22.0, 22.0, 22.0, 22.0, 22.0, 20.0, 12.0, 6.0, 6.0, 6.0]
    shift = landing_shift(motion, dt=0.4, end_idx=5, max_shift_s=5.0)
    assert 0.9 < shift <= 2.0


def test_no_shift_when_motion_stays_high() -> None:
    # the camera keeps moving (no settle ahead) -> nothing to land on, leave the cut alone
    motion = [22.0] * 11
    assert landing_shift(motion, dt=0.4, end_idx=5, max_shift_s=5.0) == 0.0


def test_ignores_a_weak_dip() -> None:
    # a shallow ~27% dip is normal motion fluctuation, not a reveal settling -> no shift
    motion = [22.0, 22.0, 22.0, 22.0, 22.0, 22.0, 16.0, 16.0, 16.0, 16.0, 16.0]
    assert landing_shift(motion, dt=0.4, end_idx=5, max_shift_s=5.0) == 0.0


def test_ignores_a_low_motion_shot() -> None:
    # the camera is barely moving at the cut -> this is not a reveal being chopped, leave it
    motion = [6.0, 6.0, 6.0, 6.0, 6.0, 6.0, 2.0, 2.0, 2.0, 2.0]
    assert landing_shift(motion, dt=0.4, end_idx=5, max_shift_s=5.0) == 0.0


def test_ignores_a_brief_settle() -> None:
    # a one-sample dip that immediately recovers is not a sustained settle
    motion = [22.0, 22.0, 22.0, 22.0, 22.0, 22.0, 6.0, 22.0, 22.0, 22.0, 22.0]
    assert landing_shift(motion, dt=0.4, end_idx=5, max_shift_s=5.0) == 0.0


def test_shift_is_bounded_by_max() -> None:
    # the settle is far away -> do not chase it beyond the bound
    motion = [22.0] * 20 + [6.0] * 5
    assert landing_shift(motion, dt=0.4, end_idx=5, max_shift_s=3.0) == 0.0
