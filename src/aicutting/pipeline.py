from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aicutting.agents.backends import detect_agent_backends
from aicutting.analysis.audio import analyze_music
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.analysis.ffprobe import probe_video
from aicutting.analysis.screenshots import extract_location_keyframes
from aicutting.analysis.video import build_candidates_from_scenes, score_candidates_from_video
from aicutting.core.artifacts import write_json_model, write_json_models
from aicutting.core.models import AnalysisReport, ClipCandidate, DroneShotType, Timeline
from aicutting.core.progress import PipelinePhase, ProgressCallback, emit_progress
from aicutting.director.drone_models import Director2Report, ShotCandidateArtifact
from aicutting.director.engine import build_director_outputs
from aicutting.director.location import resolve_location_suggestions
from aicutting.planning.effects import build_effect_plan
from aicutting.planning.engine import build_cut_plan
from aicutting.planning.story import build_story_plan
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

        if any(
            candidate.shot_type != DroneShotType.UNKNOWN
            for candidate in director_outputs.analysis.candidates
        ):
            beat_plan = build_beat_plan(report.audio)
            story_plan = build_story_plan(
                director_outputs.analysis.candidates, beat_plan, plan.target_duration_s
            )
            effect_plan = build_effect_plan(story_plan, beat_plan)
            shot_artifacts = [
                _shot_candidate_artifact(candidate) for candidate in report.candidates
            ]
            selected_count = sum(1 for item in shot_artifacts if item.selected)
            rejected_count = sum(1 for item in shot_artifacts if item.rejected)
            average_score = (
                round(
                    sum(item.drone_director_score for item in shot_artifacts)
                    / len(shot_artifacts),
                    6,
                )
                if shot_artifacts
                else 0.0
            )
            write_json_models(output_dir / "shot-candidates.json", shot_artifacts)
            write_json_model(output_dir / "beat-plan.json", beat_plan)
            write_json_model(output_dir / "story-plan.json", story_plan)
            write_json_model(output_dir / "effect-plan.json", effect_plan)
            write_json_model(
                output_dir / "director-2-report.json",
                Director2Report(
                    selected_count=selected_count,
                    rejected_count=rejected_count,
                    average_drone_director_score=average_score,
                    warnings=[],
                ),
            )

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


def _shot_candidate_artifact(candidate: ClipCandidate) -> ShotCandidateArtifact:
    selected = candidate.rejection_reason is None
    return ShotCandidateArtifact(
        asset_path=candidate.asset_path,
        start_s=candidate.start_s,
        end_s=candidate.end_s,
        shot_type=candidate.shot_type,
        selected=selected,
        rejected=not selected,
        rejection_reason=candidate.rejection_reason,
        technical_score=candidate.technical_score or candidate.quality_score,
        stability_score=candidate.smoothness_score or 0.0,
        composition_score=candidate.composition_score or 0.0,
        motion_intent_score=candidate.motion_intent_score or candidate.motion_score,
        reveal_score=candidate.reveal_score or 0.0,
        novelty_score=candidate.novelty_score or 0.0,
        drone_director_score=candidate.director_score,
        reasons=[
            f"{candidate.shot_type.value} score {candidate.director_score:.2f}",
            candidate.rejection_reason or "selected",
        ],
    )
