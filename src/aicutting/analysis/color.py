from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from aicutting.director.edit_models import FootageMoment


@dataclass(frozen=True)
class ColorSignature:
    greenness: float
    brightness: float
    saturation: float

    @property
    def order_key(self) -> float:
        # Primary axis for the visual journey: dark / desaturated lava (low) -> green moss (high).
        return self.greenness


def moment_color_signatures(
    moments: dict[str, FootageMoment],
) -> dict[str, ColorSignature]:
    # One representative frame per moment, grouped by file so each video is opened once.
    by_asset: dict[Path, list[tuple[str, float]]] = {}
    for moment_id, moment in moments.items():
        by_asset.setdefault(moment.asset_path, []).append((moment_id, moment.timestamp_s))
    signatures: dict[str, ColorSignature] = {}
    for asset_path, items in by_asset.items():
        capture = cv2.VideoCapture(str(asset_path))
        try:
            for moment_id, timestamp_s in items:
                capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_s * 1000.0)
                ok, frame = capture.read()
                if ok and frame is not None:
                    signatures[moment_id] = _signature(frame)
        finally:
            capture.release()
    return signatures


def _signature(frame: np.ndarray) -> ColorSignature:
    small = cv2.resize(frame, (160, 90))
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    hue = hsv[:, :, 0].astype(np.float32)
    sat = hsv[:, :, 1].astype(np.float32)
    val = hsv[:, :, 2].astype(np.float32)
    green = (hue >= 35) & (hue <= 85) & (sat >= 60) & (val >= 40)
    return ColorSignature(
        greenness=float(green.mean()),
        brightness=float(val.mean() / 255.0),
        saturation=float(sat.mean() / 255.0),
    )
