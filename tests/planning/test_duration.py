from aicutting.planning.duration import choose_target_duration


def test_choose_target_duration_matches_the_song() -> None:
    # A music-synced cut spans the whole track (so the song plays out and more of the footage is
    # used), clamped to a sane range -- not a fixed highlight length.
    assert choose_target_duration(total_usable_s=30.0) == 30.0  # short song -> short cut
    assert choose_target_duration(total_usable_s=182.0) == 182.0  # a 3-min song -> a full 3-min cut
    assert choose_target_duration(total_usable_s=10.0) == 15.0  # floor for tiny material
    assert choose_target_duration(total_usable_s=900.0) == 300.0  # clamp an unusually long track
