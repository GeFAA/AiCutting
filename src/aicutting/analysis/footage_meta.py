import re

from aicutting.core.models import MediaAsset

_MONTHS = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
# DJI names embed the capture moment: DJI_YYYYMMDDhhmmss_NNNN_D.MP4
_DATESTAMP = re.compile(r"(20\d{2})(\d{2})(\d{2})")


def recording_date_label(media: list[MediaAsset]) -> str | None:
    # A clean "Month Year" stamp from the earliest source file, for the when/where title.
    found: list[tuple[int, int, int]] = []
    for asset in media:
        match = _DATESTAMP.search(asset.path.name)
        if match is None:
            continue
        year, month, day = int(match[1]), int(match[2]), int(match[3])
        if 1 <= month <= 12 and 1 <= day <= 31:
            found.append((year, month, day))
    if not found:
        return None
    year, month, _day = min(found)
    return f"{_MONTHS[month]} {year}"
