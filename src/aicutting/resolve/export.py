from pathlib import Path

from aicutting.core.models import Timeline
from aicutting.resolve.edl import timeline_to_edl
from aicutting.resolve.fcpxml import timeline_to_fcpxml


def export_resolve_handoff(timeline: Timeline, output_dir: Path) -> None:
    resolve_dir = output_dir / "resolve"
    resolve_dir.mkdir(parents=True, exist_ok=True)
    (resolve_dir / "timeline.fcpxml").write_text(timeline_to_fcpxml(timeline), encoding="utf-8")
    (resolve_dir / "timeline.edl").write_text(timeline_to_edl(timeline), encoding="utf-8")
    manifest = "\n".join(str(clip.asset_path) for clip in timeline.clips) + "\n"
    (resolve_dir / "media-manifest.txt").write_text(manifest, encoding="utf-8")
