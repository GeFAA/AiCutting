from aicutting.planning.duration import choose_target_duration


def test_choose_target_duration_scales_with_material() -> None:
    assert choose_target_duration(total_usable_s=30.0) == 30.0
    assert choose_target_duration(total_usable_s=180.0) == 75.0
    assert choose_target_duration(total_usable_s=800.0) == 180.0
