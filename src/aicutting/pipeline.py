from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aicutting.agents.backends import detect_agent_backends
from aicutting.analysis.audio import analyze_music
from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.analysis.color import moment_color_signatures
from aicutting.analysis.color_match import match_clip_color_gains
from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.analysis.ffprobe import probe_video
from aicutting.analysis.footage_meta import recording_date_label
from aicutting.analysis.horizon import clip_level_degrees
from aicutting.analysis.motion import score_moment_motion, select_usable_moments
from aicutting.analysis.screenshots import (
    build_contact_sheets,
    extract_location_keyframes,
    sample_footage_moments,
)
from aicutting.analysis.video import build_candidates_from_scenes, score_candidates_from_video
from aicutting.core.artifacts import write_json_model, write_json_models
from aicutting.core.models import AnalysisReport, ClipCandidate, CutPlan, LocationTitle, Timeline
from aicutting.core.progress import PipelinePhase, ProgressCallback, emit_progress
from aicutting.core.style import STYLE_PRESETS, StylePreset
from aicutting.director.drone_models import BeatPlan
from aicutting.director.edit_agent import rate_moments
from aicutting.director.edit_models import Director3Report, FootageMoment, MomentRating
from aicutting.director.engine import build_director_outputs
from aicutting.director.location import resolve_location_suggestions
from aicutting.director.models import LocationSuggestion
from aicutting.planning.assemble import assemble_cut_plan, fallback_edit
from aicutting.planning.duration import choose_target_duration
from aicutting.planning.hero import mark_hero
from aicutting.planning.rhythm import build_rhythm_grid
from aicutting.planning.sequence import color_ordered_edit
from aicutting.planning.variants import LENGTH_VARIANTS, opening_variant
from aicutting.quality.critic import replan_if_weak, score_edit
from aicutting.render.ffmpeg import render_timeline
from aicutting.render.reframe import reframe_timeline
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
        style: StylePreset = STYLE_PRESETS["cinematic"],
        aspect: str = "16:9",
        variants: bool = False,
    ) -> PipelineResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        emit_progress(progress, PipelinePhase.ANALYZING_FOOTAGE)
        report = self.dependencies.analyze(input_dir, music_path)
        footage_s = sum(asset.duration_s for asset in report.media)
        beats = len(report.audio.beats_s)
        summary = f"{len(report.media)} videos · {footage_s:.0f}s · {beats} beats"
        emit_progress(progress, PipelinePhase.ANALYZING_FOOTAGE, message=summary)

        emit_progress(progress, PipelinePhase.IDENTIFYING_LOCATION)
        location_screenshots = extract_location_keyframes(
            _location_candidates(report),
            output_dir / "location-screenshots",
        )
        location_suggestions = resolve_location_suggestions(
            location_screenshots,
            detect_agent_backends(),
            workdir=output_dir,
        )
        emit_progress(
            progress,
            PipelinePhase.IDENTIFYING_LOCATION,
            message=_location_label(location_suggestions),
        )
        director_outputs = build_director_outputs(
            report, location_suggestions=location_suggestions
        )

        plan = _build_director_3_plan(
            director_outputs.analysis, output_dir, progress, style, aspect
        )
        title = _compose_title(
            director_outputs.director_report.title, recording_date_label(report.media)
        )
        if title is not None:
            plan = plan.model_copy(
                update={"timeline": plan.timeline.model_copy(update={"title": title})}
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

        emit_progress(progress, PipelinePhase.BUILDING_REPORT)
        report_path = _safe_build_report(output_dir)
        if report_path is not None:
            emit_progress(progress, PipelinePhase.BUILDING_REPORT, message=report_path.name)

        emit_progress(progress, PipelinePhase.EXPORTING_RESOLVE_HANDOFF)
        self.dependencies.export_resolve(plan.timeline, output_dir)
        if not dry_run:
            emit_progress(progress, PipelinePhase.RENDERING_FINAL_VIDEO)
            self.dependencies.render(plan.timeline, final_video, report.audio.path)
            if variants:
                _render_length_variants(
                    self.dependencies.render,
                    plan.timeline,
                    report.audio.path,
                    output_dir,
                    progress,
                )

        emit_progress(
            progress,
            PipelinePhase.DONE,
            message=f"{len(plan.timeline.clips)} clips · {plan.timeline.target_duration_s:.0f}s",
        )
        return PipelineResult(
            analysis=output_dir / "analysis.json",
            cut_plan=output_dir / "cut-plan.json",
            timeline=output_dir / "timeline.json",
            final_video=final_video,
            output_dir=output_dir,
        )


def _render_length_variants(
    render: Callable[[Timeline, Path, Path | None], None],
    timeline: Timeline,
    music_path: Path | None,
    output_dir: Path,
    progress: ProgressCallback | None,
) -> None:
    # Render the social length masters (teaser / short) beside the full cut. Each is the opening of
    # the full edit, so it keeps the title reveal and stays beat-synced with the music from the top.
    for variant in LENGTH_VARIANTS:
        cut = opening_variant(timeline, variant.seconds)
        if cut is None:
            continue
        emit_progress(
            progress,
            PipelinePhase.RENDERING_FINAL_VIDEO,
            message=f"{variant.name} master ({variant.seconds:.0f}s)",
        )
        render(cut, output_dir / f"final-{variant.name}.mp4", music_path)


def _compose_title(location: LocationTitle | None, date_label: str | None) -> LocationTitle | None:
    # The when/where overlay: place (where, from the vision agent) over the date (when, from the
    # footage metadata). Show whatever is available rather than nothing.
    place = (location.title or location.subtitle or "").strip() if location is not None else ""
    if place and date_label:
        confidence = location.confidence if location is not None else 1.0
        return LocationTitle(title=place, subtitle=date_label, confidence=confidence)
    if place:
        return location
    if date_label:
        return LocationTitle(title=date_label, subtitle=None, confidence=1.0)
    return None


def _location_label(suggestions: list[LocationSuggestion]) -> str:
    best = max(suggestions, key=lambda suggestion: suggestion.confidence, default=None)
    if best is None or best.place == "unknown" or not best.should_render:
        return "no confident location"
    return f"{best.title or best.place} ({best.confidence:.2f})"


def _safe_build_report(output_dir: Path) -> Path | None:
    # The HTML report is best-effort visibility; never let it break a cut.
    try:
        from importlib import import_module

        module = import_module("aicutting.report")
        result = module.build_report(output_dir)
        return result if isinstance(result, Path) else None
    except Exception:
        return None


def _location_candidates(report: AnalysisReport, limit: int = 3) -> list[ClipCandidate]:
    candidates = [
        candidate for candidate in report.candidates if candidate.rejection_reason is None
    ]
    if not candidates:
        candidates = report.candidates
    return sorted(candidates, key=lambda candidate: candidate.director_score, reverse=True)[:limit]


def _gate_moments_by_motion(moments: list[FootageMoment]) -> list[FootageMoment]:
    # Motion-aware moment selection (4.0 Pillar B): the vision agent only ever sees single still
    # thumbnails and cannot judge camera motion, so drop shaky / searching / unstable moments
    # here -- before the contact sheets and the agent -- using analysis/motion. Best-effort:
    # empty input, unreadable files, or any failure keep the original moments (never starve).
    if not moments:
        return moments
    try:
        scores = score_moment_motion(moments)
        return select_usable_moments(moments, scores)
    except Exception:
        return moments


def _build_director_3_plan(
    analysis: AnalysisReport,
    output_dir: Path,
    progress: ProgressCallback | None = None,
    style: StylePreset = STYLE_PRESETS["cinematic"],
    aspect: str = "16:9",
) -> CutPlan:
    media = analysis.media
    beat_plan = build_beat_plan(analysis.audio)
    total = analysis.audio.duration_s or sum(c.duration_s for c in analysis.candidates) or 1.0
    slots = build_rhythm_grid(beat_plan, choose_target_duration(total), pace=style.pace)
    backends = detect_agent_backends()
    moments = sample_footage_moments(media)
    moments = _gate_moments_by_motion(moments)
    moment_index: dict[str, FootageMoment] = {moment.moment_id: moment for moment in moments}
    sheets = (
        build_contact_sheets(moments, output_dir / "contact-sheets")
        if moments and any(backend.available for backend in backends)
        else []
    )
    if sheets:
        moment_count = len(moments)

        def _on_sheet(done: int, total_sheets: int) -> None:
            emit_progress(
                progress,
                PipelinePhase.RATING_FOOTAGE,
                message=f"{moment_count} moments",
                step=done,
                total=total_sheets,
            )

        _on_sheet(0, len(sheets))
        ratings = rate_moments(sheets, backends, output_dir, on_progress=_on_sheet)
    else:
        ratings = []
    kept = [rating for rating in ratings if rating.keep and rating.cinematic_score >= 0.55]
    kept = _diversify(kept, moment_index)
    if ratings:
        emit_progress(
            progress,
            PipelinePhase.RATING_FOOTAGE,
            message=f"kept {len(kept)} · rejected {len(ratings) - len(kept)}",
        )
    emit_progress(progress, PipelinePhase.DESIGNING_EDIT)
    signatures = moment_color_signatures(
        {
            rating.moment_id: moment_index[rating.moment_id]
            for rating in kept
            if rating.moment_id in moment_index
        }
    )
    edit = color_ordered_edit(kept, signatures, slots) if kept else None
    used_agent = bool(kept)
    if edit is not None:
        emit_progress(
            progress, PipelinePhase.DESIGNING_EDIT, message="colour journey: lava → green"
        )
    emit_progress(progress, PipelinePhase.ASSEMBLING_CUT)
    plan = (
        assemble_cut_plan(
            edit,
            slots,
            moment_index,
            media,
            slow_mo_speed=style.slow_mo_speed,
            slow_mo_energy=style.slow_mo_energy,
            transition_energy=style.transition_energy,
        )
        if edit is not None
        else None
    )
    fell_back = False
    if plan is None or len(plan.timeline.clips) < max(1, len(slots) // 2):
        # No agent, or the agent's edit was too sparse/infeasible -> deterministic grid fill,
        # still seeded by the agent's own kept ratings when codex rated the footage.
        fell_back = True
        if kept:
            edit = fallback_edit(kept, slots)
        else:
            durations = {asset.path: asset.duration_s for asset in media}
            safe = [
                candidate
                for candidate in analysis.candidates
                if _within_safe_zone(candidate, durations.get(candidate.asset_path, 0.0))
            ]
            ratings, moment_index = _ratings_from_candidates(safe or analysis.candidates)
            edit = fallback_edit(ratings, slots)
        plan = assemble_cut_plan(
            edit,
            slots,
            moment_index,
            media,
            slow_mo_speed=style.slow_mo_speed,
            slow_mo_energy=style.slow_mo_energy,
            transition_energy=style.transition_energy,
        )
    assert edit is not None  # always set: the agent edit or the deterministic fill
    if not fell_back and kept:
        # Self-critic re-plan: if the agent cut graded weak, assemble the deterministic fallback as
        # an alternative and keep whichever the critic grades higher (a no-op for a strong cut).
        primary = plan
        plan = replan_if_weak(
            plan,
            beat_plan.beats_s,
            lambda: assemble_cut_plan(
                fallback_edit(kept, slots),
                slots,
                moment_index,
                media,
                slow_mo_speed=style.slow_mo_speed,
                slow_mo_energy=style.slow_mo_energy,
                transition_energy=style.transition_energy,
            ),
        )
        if plan is not primary:
            emit_progress(
                progress, PipelinePhase.ASSEMBLING_CUT, message="self-critic re-planned a weak cut"
            )
    transitions = sum(
        1 for clip in plan.timeline.clips if clip.transition_in.kind.value != "hard_cut"
    )
    emit_progress(
        progress,
        PipelinePhase.ASSEMBLING_CUT,
        message=f"{len(plan.timeline.clips)} cuts on the beat · {transitions} transitions",
    )
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
    return _finalize_timeline(plan, style, aspect, beat_plan, output_dir, progress)


def _finalize_timeline(
    plan: CutPlan,
    style: StylePreset,
    aspect: str,
    beat_plan: BeatPlan,
    output_dir: Path,
    progress: ProgressCallback | None,
) -> CutPlan:
    # Finish the assembled cut: level tilted horizons, colour-match the clips toward one consistent
    # look, apply the style's grade (the renderer reads grade_strength), reframe to the requested
    # social aspect (9:16 / 1:1; 16:9 leaves the source master untouched), then run the read-only
    # self-critic -- which grades the cut but never alters it, so a low grade is reported, not
    # silently "fixed".
    hero = mark_hero(plan.timeline, beat_plan)
    levelled = _level_horizons(hero)
    matched = _match_clip_colors(levelled)
    graded = matched.model_copy(update={"grade_strength": style.grade_strength})
    reframed = reframe_timeline(graded, aspect)
    quality = score_edit(reframed, beat_plan.beats_s)
    write_json_model(output_dir / "edit-quality.json", quality)
    emit_progress(
        progress,
        PipelinePhase.ASSEMBLING_CUT,
        message=f"self-critic: grade {quality.grade} ({quality.overall:.0%})",
    )
    return plan.model_copy(update={"timeline": reframed})


def _level_horizons(timeline: Timeline) -> Timeline:
    # Horizon levelling (best-effort): rotate clips with a clearly tilted horizon back to level.
    # Reading frames can fail on unreadable / fake files, so any failure leaves the timeline as-is.
    if not timeline.clips:
        return timeline
    try:
        degrees = clip_level_degrees(timeline.clips)
    except Exception:
        return timeline
    if not any(degrees):
        return timeline
    clips = [
        clip.model_copy(update={"level_deg": deg})
        for clip, deg in zip(timeline.clips, degrees, strict=False)
    ]
    return timeline.model_copy(update={"clips": clips})


def _match_clip_colors(timeline: Timeline) -> Timeline:
    # Cross-clip colour matching (best-effort): nudge each clip toward one consistent look. Reading
    # frames can fail on unreadable / fake files, so any failure leaves the timeline untouched.
    if len(timeline.clips) < 2:
        return timeline
    try:
        gains = match_clip_color_gains(timeline.clips)
    except Exception:
        return timeline
    clips = [
        clip.model_copy(update={"color_gain": gain})
        for clip, gain in zip(timeline.clips, gains, strict=False)
    ]
    return timeline.model_copy(update={"clips": clips})


def _diversify(
    kept: list[MomentRating], moments: dict[str, FootageMoment], min_gap_s: float = 8.0
) -> list[MomentRating]:
    # Drop near-duplicate keeps (same file + shot type within a few seconds), keeping the highest
    # scored, so the montage shows variety instead of repeating one composition.
    chosen: list[MomentRating] = []
    seen: dict[tuple[Path, str], list[float]] = {}
    for rating in sorted(kept, key=lambda item: item.cinematic_score, reverse=True):
        moment = moments.get(rating.moment_id)
        if moment is None:
            chosen.append(rating)
            continue
        bucket = (moment.asset_path, rating.shot_type.value)
        times = seen.setdefault(bucket, [])
        if any(abs(moment.timestamp_s - other) < min_gap_s for other in times):
            continue
        times.append(moment.timestamp_s)
        chosen.append(rating)
    return chosen


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
