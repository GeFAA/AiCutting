from pathlib import Path

import cv2

from aicutting.core.models import ClipCandidate


def extract_location_keyframes(
    candidates: list[ClipCandidate],
    output_dir: Path,
    max_images: int = 3,
) -> list[Path]:
    if max_images <= 0:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    images: list[Path] = []
    for candidate in candidates:
        if len(images) >= max_images:
            break
        if not candidate.asset_path.exists():
            continue

        image_path = _extract_midpoint_frame(candidate, output_dir, len(images) + 1)
        if image_path is not None:
            images.append(image_path)

    return images


def _extract_midpoint_frame(
    candidate: ClipCandidate,
    output_dir: Path,
    index: int,
) -> Path | None:
    capture = cv2.VideoCapture(str(candidate.asset_path))
    try:
        if not capture.isOpened():
            return None

        midpoint_s = round((candidate.start_s + candidate.end_s) / 2, 3)
        capture.set(cv2.CAP_PROP_POS_MSEC, midpoint_s * 1000.0)
        ok, frame = capture.read()
        if not ok or frame is None:
            return None

        image_path = output_dir / (
            f"location-{index:02d}-{candidate.asset_path.stem}-{midpoint_s:.3f}s.jpg"
        )
        if not cv2.imwrite(str(image_path), frame):
            return None
        return image_path
    finally:
        capture.release()
