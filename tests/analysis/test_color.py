import numpy as np

from aicutting.analysis.color import _signature


def test_signature_scores_green_higher_than_lava() -> None:
    green = np.full((90, 160, 3), (40, 180, 40), dtype=np.uint8)  # vivid green (BGR)
    lava = np.full((90, 160, 3), (22, 20, 24), dtype=np.uint8)  # near-black basalt

    assert _signature(green).greenness > _signature(lava).greenness
    assert _signature(green).order_key == _signature(green).greenness


def test_signature_brightness_tracks_value() -> None:
    bright = np.full((90, 160, 3), (220, 220, 220), dtype=np.uint8)
    dark = np.full((90, 160, 3), (25, 25, 25), dtype=np.uint8)

    assert _signature(bright).brightness > _signature(dark).brightness
