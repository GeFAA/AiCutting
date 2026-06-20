import subprocess
from pathlib import Path

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import Timeline


def build_ffmpeg_command(
    timeline: Timeline,
    output_path: Path,
    music_path: Path | None,
) -> list[str]:
    inputs: list[str] = []
    for clip in timeline.clips:
        inputs.extend(["-i", _ffmpeg_path(clip.asset_path)])
    if music_path is not None:
        inputs.extend(["-i", _ffmpeg_path(music_path)])

    video_filters: list[str] = []
    concat_inputs: list[str] = []
    for index, clip in enumerate(timeline.clips):
        label = f"v{index}"
        video_filters.append(
            f"[{index}:v]trim=start={clip.source_start_s}:end={clip.source_end_s},"
            f"setpts=PTS-STARTPTS,scale={timeline.width}:{timeline.height},fps={timeline.fps}[{label}]"
        )
        concat_inputs.append(f"[{label}]")

    filter_complex = ";".join(video_filters)
    if concat_inputs:
        filter_complex = (
            f"{filter_complex};{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[vout]"
        )

    command = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[vout]"]
    if music_path is not None:
        command.extend(["-shortest", "-map", f"{len(timeline.clips)}:a"])
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", _ffmpeg_path(output_path)])
    return command


def render_timeline(timeline: Timeline, output_path: Path, music_path: Path | None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(timeline, output_path=output_path, music_path=music_path)
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise ExternalToolError("FFmpeg is not available on PATH.") from exc
    if result.returncode != 0:
        raise ExternalToolError(f"FFmpeg render failed: {result.stderr.strip()}")


def _ffmpeg_path(path: Path) -> str:
    return path.as_posix()
