from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aicutting.analysis.audio import analyze_music
from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.analysis.ffprobe import probe_video
from aicutting.analysis.video import build_candidates_from_scenes
from aicutting.core.artifacts import write_json_model
from aicutting.core.models import AnalysisReport, Timeline
from aicutting.planning.engine import build_cut_plan
from aicutting.render.ffmpeg import render_timeline
from aicutting.resolve.export import export_resolve_handoff


@dataclass(frozen=True)
class PipelineResult:
    analysis: Path
    cut_plan: Path
    timeline: Path
    final_video: Path
    output_dir: Path


@dataclass(frozen=True)
class PipelineDependencies:
    analyze: Callable[[Path, Path | None], AnalysisReport]
    render: Callable[[Timeline, Path, Path | None], None]
    export_resolve: Callable[[Timeline, Path], None]


def default_analyze(input_dir: Path, music_path: Path | None) -> AnalysisReport:
    videos = discover_videos(input_dir)
    music = discover_music(music_path)
    media = [probe_video(path) for path in videos]
    candidates = []
    for asset in media:
        scenes = [(0.0, min(asset.duration_s, 6.0))]
        candidates.extend(
            build_candidates_from_scenes(
                asset,
                scenes,
                quality_score=0.7,
                motion_score=0.4,
            )
        )
    audio = analyze_music(music)
    return AnalysisReport(media=media, candidates=candidates, audio=audio)


class CutPipeline:
    def __init__(self, dependencies: PipelineDependencies | None = None) -> None:
        self.dependencies = dependencies or PipelineDependencies(
            analyze=default_analyze,
            render=render_timeline,
            export_resolve=export_resolve_handoff,
        )

    def cut(
        self,
        input_dir: Path,
        music_path: Path | None,
        output_dir: Path,
        dry_run: bool,
    ) -> PipelineResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = self.dependencies.analyze(input_dir, music_path)
        plan = build_cut_plan(report)
        final_video = output_dir / "final.mp4"

        write_json_model(output_dir / "analysis.json", report)
        write_json_model(output_dir / "cut-plan.json", plan)
        write_json_model(output_dir / "timeline.json", plan.timeline)
        self.dependencies.export_resolve(plan.timeline, output_dir)
        if not dry_run:
            self.dependencies.render(plan.timeline, final_video, report.audio.path)

        return PipelineResult(
            analysis=output_dir / "analysis.json",
            cut_plan=output_dir / "cut-plan.json",
            timeline=output_dir / "timeline.json",
            final_video=final_video,
            output_dir=output_dir,
        )
