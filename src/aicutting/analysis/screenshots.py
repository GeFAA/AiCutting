from pathlib import Path

import cv2
import numpy as np

from aicutting.core.models import ClipCandidate, MediaAsset
from aicutting.director.edit_models import ContactSheet, FootageMoment


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


def sample_footage_moments(
    media: list[MediaAsset],
    trim_s: float = 12.0,
    stride_s: float = 4.0,
    max_moments: int = 96,
) -> list[FootageMoment]:
    # Collect candidates from EVERY file first; subsample evenly only if there are too many. (A
    # per-file cap would exhaust the budget on the first file and never sample the others, which
    # is what made the whole edit repeat a single source clip.)
    raw: list[tuple[Path, float]] = []
    for asset in media:
        if asset.duration_s - 2 * trim_s <= stride_s:  # short clip: proportional 10% trim
            edge = max(0.0, asset.duration_s * 0.1)
            start, end = edge, asset.duration_s - edge
        else:
            start, end = trim_s, asset.duration_s - trim_s
        cursor = start
        while cursor <= end:
            raw.append((asset.path, round(cursor, 3)))
            cursor += stride_s
    if max_moments > 0 and len(raw) > max_moments:
        step = len(raw) / max_moments
        raw = [raw[int(i * step)] for i in range(max_moments)]
    return [
        FootageMoment(moment_id=f"m{index + 1:03d}", asset_path=path, timestamp_s=timestamp)
        for index, (path, timestamp) in enumerate(raw)
    ]


def build_contact_sheets(
    moments: list[FootageMoment],
    output_dir: Path,
    per_sheet: int = 12,
    columns: int = 4,
    thumb_w: int = 320,
) -> list[ContactSheet]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sheets: list[ContactSheet] = []
    for chunk_start in range(0, len(moments), per_sheet):
        chunk = moments[chunk_start : chunk_start + per_sheet]
        tiles, ids = _render_tiles(chunk, thumb_w)
        if not tiles:
            continue
        sheet_image = _tile_grid(tiles, columns)
        sheet_path = output_dir / f"contact-sheet-{len(sheets) + 1:02d}.jpg"
        cv2.imwrite(str(sheet_path), sheet_image)
        sheets.append(ContactSheet(path=sheet_path, moment_ids=ids))
    return sheets


def _render_tiles(
    chunk: list[FootageMoment], thumb_w: int
) -> tuple[list[np.ndarray], list[str]]:
    by_asset: dict[Path, list[FootageMoment]] = {}
    for moment in chunk:
        by_asset.setdefault(moment.asset_path, []).append(moment)

    rendered: dict[str, np.ndarray] = {}
    for asset_path, items in by_asset.items():
        capture = cv2.VideoCapture(str(asset_path))
        try:
            if not capture.isOpened():
                continue
            for moment in items:
                capture.set(cv2.CAP_PROP_POS_MSEC, moment.timestamp_s * 1000.0)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                rendered[moment.moment_id] = _label_thumb(frame, moment, thumb_w)
        finally:
            capture.release()

    tiles: list[np.ndarray] = []
    ids: list[str] = []
    for moment in chunk:
        thumb = rendered.get(moment.moment_id)
        if thumb is not None:
            tiles.append(thumb)
            ids.append(moment.moment_id)
    return tiles, ids


def _label_thumb(frame: np.ndarray, moment: FootageMoment, thumb_w: int) -> np.ndarray:
    height, width = frame.shape[:2]
    thumb_h = max(1, int(height * (thumb_w / max(1, width))))
    thumb = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
    label = f"{moment.moment_id} {moment.asset_path.stem} {moment.timestamp_s:.0f}s"
    cv2.rectangle(thumb, (0, 0), (thumb_w, 22), (0, 0, 0), -1)
    cv2.putText(
        thumb, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA
    )
    return thumb


def _tile_grid(tiles: list[np.ndarray], columns: int) -> np.ndarray:
    thumb_h = max(tile.shape[0] for tile in tiles)
    thumb_w = max(tile.shape[1] for tile in tiles)
    blank = np.zeros((thumb_h, thumb_w, 3), dtype=np.uint8)
    padded = [
        tile if tile.shape[:2] == (thumb_h, thumb_w) else cv2.resize(tile, (thumb_w, thumb_h))
        for tile in tiles
    ]
    rows: list[np.ndarray] = []
    for row_start in range(0, len(padded), columns):
        row = padded[row_start : row_start + columns]
        while len(row) < columns:
            row.append(blank)
        rows.append(np.hstack(row))
    return np.vstack(rows)
