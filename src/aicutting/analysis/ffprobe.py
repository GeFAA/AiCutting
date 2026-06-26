import json
import subprocess
from pathlib import Path

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import MediaAsset


def _parse_fps(rate: str) -> float:
    numerator, denominator = rate.split("/")
    denominator_value = float(denominator)
    if denominator_value == 0:
        return 0.0
    return float(numerator) / denominator_value


def probe_video(path: Path) -> MediaAsset:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        raise ExternalToolError(
            f"ffprobe is not available while probing {path}. Ensure ffprobe is on PATH."
        ) from error

    if result.returncode != 0:
        raise ExternalToolError(f"ffprobe failed for {path}: {result.stderr.strip()}")

    try:
        payload = json.loads(result.stdout)
        video_stream = next(
            stream for stream in payload["streams"] if stream.get("codec_type") == "video"
        )
        return MediaAsset(
            path=path,
            duration_s=float(payload["format"]["duration"]),
            width=int(video_stream["width"]),
            height=int(video_stream["height"]),
            fps=_parse_fps(str(video_stream["avg_frame_rate"])),
        )
    except (json.JSONDecodeError, KeyError, StopIteration, TypeError, ValueError) as error:
        raise ExternalToolError(f"Invalid ffprobe output for {path}") from error
