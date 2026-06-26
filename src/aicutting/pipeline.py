from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aicutting.agents.backends import detect_agent_backends
from aicutting.analysis.audio import analyze_music
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.analysis.ffprobe import probe_video
from aicutting.analysis.screenshots import (
    build_contact_sheets,
    extract_location_keyframes,
    sample_footage_moments,
)
from aicutting.analysis.video import build_candidates_from_scenes, score_candidates_from_video
from aicutting.core.artifacts import write_json_model, write_json_models
from aicutting.core.models import AnalysisReport, ClipCandidate, CutPlan, Timeline
from aicutting.core.progress import PipelinePhase, ProgressCallback, emit_progress
from aicutting.director.edit_agent import decide_edit, rate_moments
from aicutting.director.edit_models import Director3Report, FootageMoment, MomentRating
from aicutting.director.engine import build_director_outputs
from aicutting.director.location import resolve_location_suggestions
from aicutting.planning.assemble import assemble_cut_plan, fallback_edit
from aicutting.planning.duration import choose_target_duration
from aicutting.planning.rhythm import build_rhythm_grid
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
        plan = _build_director_3_plan(director_outputs.analysis, output_dir)
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


def _build_director_3_plan(analysis: AnalysisReport, output_dir: Path) -> CutPlan:
    media = analysis.media
    beat_plan = build_beat_plan(analysis.audio)
    total = analysis.audio.duration_s or sum(c.duration_s for c in analysis.candidates) or 1.0
    slots = build_rhythm_grid(beat_plan, choose_target_duration(total))
    backends = detect_agent_backends()
    moments = sample_footage_moments(media)
    moment_index: dict[str, FootageMoment] = {moment.moment_id: moment for moment in moments}
    sheets = (
        build_contact_sheets(moments, output_dir / "contact-sheets")
        if moments and any(backend.available for backend in backends)
        else []
    )
    ratings = rate_moments(sheets, backends, output_dir) if sheets else []
    kept = [rating for rating in ratings if rating.keep]
    edit = decide_edit(kept, slots, backends, output_dir) if kept else None
    used_agent = edit is not None
    if edit is None:
        durations = {asset.path: asset.duration_s for asset in media}
        safe = [
            candidate
            for candidate in analysis.candidates
            if _within_safe_zone(candidate, durations.get(candidate.asset_path, 0.0))
        ]
        fallback_ratings, fallback_moments = _ratings_from_candidates(safe or analysis.candidates)
        moment_index = fallback_moments
        ratings = ratings or fallback_ratings
        edit = fallback_edit(fallback_ratings, slots)
    plan = assemble_cut_plan(edit, slots, moment_index, media)
    write_json_models(output_dir / "footage-ratings.json", ratings)
    write_json_models(output_dir / "rhythm-grid.json", slots)
    write_json_model(output_dir / "edit-decision.json", edit)
    write_json_model(
        output_dir / "director-3-report.json",
        Director3Report(
            used_agent=used_agent,
            backend=next((backend.name for backend in backends if backend.available), None),
            rated_moments=len(ratings),
            kept_moments=sum(1 for rating in ratings if rating.keep),
            timeline_clips=len(plan.timeline.clips),
            warnings=[] if plan.timeline.clips else ["No clips could be assembled."],
        ),
    )
    return plan


def _ratings_from_candidates(
    candidates: list[ClipCandidate],
) -> tuple[list[MomentRating], dict[str, FootageMoment]]:
    ratings: list[MomentRating] = []
    moments: dict[str, FootageMoment] = {}
    for index, candidate in enumerate(candidates):
        if candidate.rejection_reason:
            continue
        moment_id = f"c{index:03d}"
        ratings.append(
            MomentRating(
                moment_id=moment_id,
                cinematic_score=candidate.director_score,
                shot_type=candidate.shot_type,
                keep=True,
                reason="deterministic fallback",
            )
        )
        moments[moment_id] = FootageMoment(
            moment_id=moment_id,
            asset_path=candidate.asset_path,
            timestamp_s=round((candidate.start_s + candidate.end_s) / 2, 3),
        )
    return ratings, moments


def _within_safe_zone(
    candidate: ClipCandidate, file_duration_s: float, trim_s: float = 12.0
) -> bool:
    # Reject windows in the takeoff/landing zone at the very start/end of each source file.
    if file_duration_s <= 0:
        return True
    midpoint = (candidate.start_s + candidate.end_s) / 2
    edge = min(trim_s, file_duration_s * 0.1)
    return edge <= midpoint <= file_duration_s - edge
