import subprocess
from pathlib import Path

from aicutting.core.errors import ExternalToolError
from aicutting.core.models import Timeline, TimelineClip, TransitionType
from aicutting.render.titles import build_title_overlay, discover_font

# Transition kinds rendered as an FFmpeg xfade. 2.0 effect kinds fall back to a stable xfade
# variant until dedicated filters (zoompan, speed ramps) are wired in.
_XFADE_KINDS = {
    TransitionType.DISSOLVE,
    TransitionType.SMOOTH_ZOOM,
    TransitionType.WHIP_BLUR,
    TransitionType.FLASH_CUT,
}

# A restrained cinematic grade applied to every clip: gentle contrast + saturation and a subtle
# teal-orange split-tone (cool shadows, warm highlights) so the whole film shares one graded look.
# `strength` scales it: the eq gains pivot around 1.0 and the colour-balance offsets around 0.0, so
# strength=1.0 reproduces the shipped grade byte-for-byte and 0.0 is neutral. A style preset can
# soften (chill/vlog) or strengthen (epic) the look via Timeline.grade_strength.
def _color_grade(strength: float) -> str:
    def fmt(value: float) -> str:
        # `+ 0.0` normalises any -0.0 so a neutral grade reads `0`, not `-0`.
        return f"{round(value, 4) + 0.0:g}"

    return (
        f",eq=contrast={fmt(1.0 + 0.06 * strength)}:saturation={fmt(1.0 + 0.1 * strength)}"
        f",colorbalance=rs={fmt(-0.02 * strength)}:bs={fmt(0.03 * strength)}"
        f":rh={fmt(0.03 * strength)}:bh={fmt(-0.02 * strength)}"
    )


def _scale_clause(timeline: Timeline) -> str:
    # A landscape master scales straight to the frame (the source is already 16:9), byte-identical
    # to the shipped behaviour. A vertical/square master instead *covers* the frame and centre-crops
    # so a 16:9 source fills a 9:16 / 1:1 frame with no stretched pixels and no letterbox bars.
    if timeline.height >= timeline.width:
        return (
            f"scale={timeline.width}:{timeline.height}:force_original_aspect_ratio=increase,"
            f"crop={timeline.width}:{timeline.height}"
        )
    return f"scale={timeline.width}:{timeline.height}"


def build_ffmpeg_command(
    timeline: Timeline,
    output_path: Path,
    music_path: Path | None,
) -> list[str]:
    inputs: list[str] = []
    for clip in timeline.clips:
        inputs.extend(
            [
                "-ss",
                _format_seconds(clip.source_start_s),
                "-t",
                _format_seconds(clip.source_duration_s),
                "-i",
                _ffmpeg_path(clip.asset_path),
            ]
        )
    if music_path is not None:
        inputs.extend(["-i", _ffmpeg_path(music_path)])

    video_filters: list[str] = []
    concat_inputs: list[str] = []
    grade = _color_grade(timeline.grade_strength)
    scale = _scale_clause(timeline)
    for index, clip in enumerate(timeline.clips):
        label = f"v{index}"
        animation = _clip_animation(clip, timeline, index)
        # Slow-mo clips (speed < 1) stretch their timestamps so the shorter source fills the slot;
        # speed 1.0 keeps the plain reset so existing behaviour is byte-identical.
        pts = "PTS-STARTPTS" if clip.speed == 1.0 else f"(PTS-STARTPTS)/{clip.speed:g}"
        video_filters.append(
            f"[{index}:v]setpts={pts},{scale},"
            f"fps={timeline.fps},format=yuv420p{grade}{animation},settb=AVTB[{label}]"
        )
        concat_inputs.append(f"[{label}]")

    if timeline.title is not None:
        base_filter = _compose_video_filter(
            timeline, video_filters, concat_inputs, output_label="vbase"
        )
        title_graph = build_title_overlay(
            timeline.title,
            discover_font(),
            timeline.width,
            timeline.height,
            timeline.fps,
        )
        filter_complex = f"{base_filter};{title_graph}"
    else:
        filter_complex = _compose_video_filter(timeline, video_filters, concat_inputs)

    command = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[vout]"]
    if music_path is not None:
        command.extend(["-shortest", "-map", f"{len(timeline.clips)}:a"])
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", _ffmpeg_path(output_path)])
    return command


def render_timeline(timeline: Timeline, output_path: Path, music_path: Path | None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(timeline, output_path=output_path, music_path=music_path)
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise ExternalToolError("FFmpeg is not available on PATH.") from exc
    if result.returncode != 0:
        raise ExternalToolError(f"FFmpeg render failed: {result.stderr.strip()}")


def _ffmpeg_path(path: Path) -> str:
    return path.as_posix()


def _compose_video_filter(
    timeline: Timeline,
    video_filters: list[str],
    concat_inputs: list[str],
    output_label: str = "vout",
) -> str:
    if not concat_inputs:
        return ";".join(video_filters)

    has_rendered_transition = any(
        clip.transition_in.kind in _XFADE_KINDS and clip.transition_in.duration_s > 0
        for clip in timeline.clips[1:]
    )
    if not has_rendered_transition:
        return (
            f"{';'.join(video_filters)};"
            f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[{output_label}]"
        )

    chain_filters = list(video_filters)
    current_label = "v0"
    output_duration_s = timeline.clips[0].timeline_duration_s
    last_clip_index = len(timeline.clips) - 1
    for index, clip in enumerate(timeline.clips[1:], start=1):
        clip_duration_s = clip.timeline_duration_s
        next_label = output_label if index == last_clip_index else f"x{index}"
        if clip.transition_in.kind in _XFADE_KINDS and clip.transition_in.duration_s > 0:
            transition_name = _xfade_transition_name(clip.transition_in.kind)
            transition_duration_s = min(
                clip.transition_in.duration_s,
                max(0.001, output_duration_s - 0.001),
                max(0.001, clip_duration_s - 0.001),
            )
            offset_s = max(0.0, output_duration_s - transition_duration_s)
            chain_filters.append(
                f"[{current_label}][v{index}]xfade=transition={transition_name}:"
                f"duration={_format_seconds(transition_duration_s)}:"
                f"offset={_format_seconds(offset_s)}[{next_label}]"
            )
            output_duration_s = output_duration_s + clip_duration_s - transition_duration_s
        else:
            chain_filters.append(f"[{current_label}][v{index}]concat=n=2:v=1:a=0[{next_label}]")
            output_duration_s += clip_duration_s
        current_label = next_label

    return ";".join(chain_filters)


def _format_seconds(value: float) -> str:
    return str(round(value, 3))


def _xfade_transition_name(kind: TransitionType) -> str:
    return {
        TransitionType.WHIP_BLUR: "fadeblack",
        TransitionType.SMOOTH_ZOOM: "fade",  # gentle crossfade (the push-in carries the motion)
        TransitionType.FLASH_CUT: "fadewhite",
    }.get(kind, "fade")


# Anchor points the push-in drifts toward — cycling these gives each held shot a different,
# subtly directional Ken Burns move instead of every clip zooming dead-centre.
_PUSH_TARGETS: tuple[tuple[str, str], ...] = (
    ("iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # centre
    ("iw-iw/zoom", "0"),  # toward top-right
    ("0", "ih-ih/zoom"),  # toward bottom-left
    ("0", "0"),  # toward top-left
    ("iw-iw/zoom", "ih-ih/zoom"),  # toward bottom-right
)


def _clip_animation(clip: TimelineClip, timeline: Timeline, index: int) -> str:
    # A SMOOTH_ZOOM clip gets a pronounced push-in (placed on accents); any long held shot gets a
    # gentle push-in so it reads as cinematic motion instead of a frozen frame. The anchor cycles
    # so consecutive held shots move toward different corners rather than all pushing dead-centre.
    target = _PUSH_TARGETS[index % len(_PUSH_TARGETS)]
    if clip.transition_in.kind == TransitionType.SMOOTH_ZOOM:
        return _zoompan(timeline, increment=0.0015, cap=1.12, target=target)
    if clip.timeline_duration_s >= 4.0:
        return _zoompan(timeline, increment=0.0004, cap=1.10, target=target)
    return ""


def _zoompan(timeline: Timeline, increment: float, cap: float, target: tuple[str, str]) -> str:
    # zoompan with d=1 emits one output frame per input frame, so the zoom accumulates over the
    # clip without changing its frame count (d=duration would explode the frames on a video input).
    # fps must match the per-clip `fps=` filter exactly: a rounded value resolves to a different
    # rational (e.g. 599401/10000 vs 60000/1001) and xfade rejects the mismatch.
    x, y = target
    return (
        f",zoompan=z='min(zoom+{increment:g},{cap:g})':d=1"
        f":x='{x}':y='{y}'"
        f":s={timeline.width}x{timeline.height}:fps={timeline.fps}"
    )
