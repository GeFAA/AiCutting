from aicutting.core.models import AnalysisReport, CutPlan, Timeline, TimelineClip
from aicutting.planning.duration import choose_target_duration
from aicutting.planning.ranking import rank_candidates
from aicutting.planning.transitions import choose_transition


def build_cut_plan(report: AnalysisReport) -> CutPlan:
    total_usable_s = sum(candidate.duration_s for candidate in report.candidates)
    target_duration_s = choose_target_duration(total_usable_s)
    ranked = rank_candidates(report.candidates)
    base_asset = report.media[0]

    clips: list[TimelineClip] = []
    timeline_cursor = 0.0
    previous = None
    for index, candidate in enumerate(ranked):
        if timeline_cursor >= target_duration_s:
            break
        remaining = target_duration_s - timeline_cursor
        clip_duration = min(candidate.duration_s, remaining, 6.0 if report.audio.beats_s else 5.0)
        energy = (
            report.audio.energy[index % len(report.audio.energy)]
            if report.audio.energy
            else 0.2
        )
        transition = choose_transition(previous=previous, current=candidate, beat_energy=energy)
        clips.append(
            TimelineClip(
                asset_path=candidate.asset_path,
                source_start_s=candidate.start_s,
                source_end_s=candidate.start_s + clip_duration,
                timeline_start_s=round(timeline_cursor, 3),
                transition_in=transition,
                speed=1.0,
                color_intent="subtle_cinematic",
            )
        )
        timeline_cursor = round(timeline_cursor + clip_duration, 3)
        previous = candidate

    timeline = Timeline(
        target_duration_s=target_duration_s,
        clips=clips,
        fps=base_asset.fps,
        width=base_asset.width,
        height=base_asset.height,
    )
    return CutPlan(
        target_duration_s=target_duration_s,
        style="adaptive_clean_cinematic",
        timeline=timeline,
        notes=["Generated from deterministic analysis signals."],
    )
