from aicutting.core.models import Timeline


def timeline_to_edl(timeline: Timeline) -> str:
    lines = ["TITLE: AiCutting", "FCM: NON-DROP FRAME"]
    for index, clip in enumerate(timeline.clips, start=1):
        source_in = _format_timecode(clip.source_start_s, timeline.fps)
        source_out = _format_timecode(clip.source_end_s, timeline.fps)
        record_in = _format_timecode(clip.timeline_start_s, timeline.fps)
        record_out = _format_timecode(
            clip.timeline_start_s + clip.timeline_duration_s,
            timeline.fps,
        )
        lines.append(
            f"{index:03d}  AX       V     C        "
            f"{source_in} {source_out} {record_in} {record_out}"
        )
        lines.append(f"* FROM CLIP NAME: {clip.asset_path.name}")
    return "\n".join(lines) + "\n"


def _format_timecode(seconds: float, fps: float) -> str:
    frame_rate = int(round(fps))
    total_frames = int(round(seconds * frame_rate))
    frames = total_frames % frame_rate
    total_seconds = total_frames // frame_rate
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"
