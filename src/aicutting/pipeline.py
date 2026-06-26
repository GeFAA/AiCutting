from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aicutting.agents.backends import detect_agent_backends
from aicutting.analysis.audio import analyze_music
from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.analysis.ffprobe import probe_video
from aicutting.analysis.screenshots import extract_location_keyframes
from aicutting.analysis.video import build_candidates_from_scenes, score_candidates_from_video
from aicutting.core.artifacts import write_json_model, write_json_models
from aicutting.core.models import AnalysisReport, ClipCandidate, Timeline
from aicutting.core.progress import PipelinePhase, ProgressCallback, emit_progress
from aicutting.director.engine import build_director_outputs
from aicutting.director.location import resolve_location_suggestions
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
        base_candidates = build_candidates_from_scenes(
            asset,
            [(0.0, asset.duration_s)],
            quality_score=0.7,
            motion_score=0.4,
        )
        candidates.extend(score_candidates_from_video(asset, base_candidates))
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
        progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        emit_progress(progress, PipelinePhase.ANALYZING_FOOTAGE, step=1, total=4)
        report = self.dependencies.analyze(input_dir, music_path)
        location_screenshots = extract_location_keyframes(
            _location_candidates(report),
            output_dir / "location-screenshots",
        )
        location_suggestions = resolve_location_suggestions(
            location_screenshots,
            detect_agent_backends(),
            workdir=output_dir,
        )
        director_outputs = build_director_outputs(
            report, location_suggestions=location_suggestions
        )

        emit_progress(progress, PipelinePhase.PLANNING_CUT, step=2, total=4)
        plan = build_cut_plan(director_outputs.analysis)
        if director_outputs.director_report.title is not None:
            plan = plan.model_copy(
                update={
                    "timeline": plan.timeline.model_copy(
                        update={"title": director_outputs.director_report.title}
                    )
                }
            )
        final_video = output_dir / "final.mp4"

        write_json_model(output_dir / "analysis.json", director_outputs.analysis)
        write_json_model(output_dir / "cut-plan.json", plan)
        write_json_model(output_dir / "timeline.json", plan.timeline)
        write_json_model(output_dir / "director-report.json", director_outputs.director_report)
        write_json_models(
            output_dir / "rejected-segments.json", director_outputs.rejected_segments
        )
        write_json_models(output_dir / "location-suggestions.json", location_suggestions)

        emit_progress(progress, PipelinePhase.EXPORTING_RESOLVE_HANDOFF, step=3, total=4)
        self.dependencies.export_resolve(plan.timeline, output_dir)
        if not dry_run:
            emit_progress(progress, PipelinePhase.RENDERING_FINAL_VIDEO, step=4, total=4)
            self.dependencies.render(plan.timeline, final_video, report.audio.path)

        emit_progress(progress, PipelinePhase.DONE)
        return PipelineResult(
            analysis=output_dir / "analysis.json",
            cut_plan=output_dir / "cut-plan.json",
            timeline=output_dir / "timeline.json",
            final_video=final_video,
            output_dir=output_dir,
        )


def _location_candidates(report: AnalysisReport, limit: int = 3) -> list[ClipCandidate]:
    candidates = [
        candidate for candidate in report.candidates if candidate.rejection_reason is None
    ]
    if not candidates:
        candidates = report.candidates
    return sorted(candidates, key=lambda candidate: candidate.director_score, reverse=True)[:limit]
