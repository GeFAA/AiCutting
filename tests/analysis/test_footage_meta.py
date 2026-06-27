from pathlib import Path

from aicutting.analysis.footage_meta import recording_date_label
from aicutting.core.models import MediaAsset


def _asset(name: str) -> MediaAsset:
    return MediaAsset(path=Path(name), duration_s=10.0, width=1920, height=1080, fps=30.0)


def test_recording_date_label_reads_dji_filename() -> None:
    media = [_asset("DJI_20250617162219_0043_D.MP4"), _asset("DJI_20250615194645_0010_D.MP4")]
    # earliest file wins -> 15 June 2025
    assert recording_date_label(media) == "June 2025"


def test_recording_date_label_none_without_datestamp() -> None:
    assert recording_date_label([_asset("clip.mp4")]) is None
