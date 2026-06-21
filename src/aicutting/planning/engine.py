from aicutting.core.models import AnalysisReport, AudioAnalysis, CutPlan, Timeline, TimelineClip
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
    for candidate in ranked:
        if timeline_cursor >= target_duration_s:
            break
        remaining = target_duration_s - timeline_cursor
        clip_duration = _choose_clip_duration(
            candidate.duration_s,
            remaining,
            report.audio,
            timeline_cursor,
        )
        energy = _audio_energy_at(report.audio, timeline_cursor)
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


def _choose_clip_duration(
    candidate_duration_s: float,
    remaining_s: float,
    audio: AudioAnalysis,
    timeline_cursor_s: float,
) -> float:
    max_duration = min(candidate_duration_s, remaining_s)
    if max_duration <= 0:
        return 0.0
    if not audio.beats_s:
        return round(min(max_duration, 5.0), 3)

    energy = _audio_energy_at(audio, timeline_cursor_s)
    if energy >= 0.75:
        desired_duration = 2.5
    elif energy >= 0.45:
        desired_duration = 3.75
    else:
        desired_duration = 5.5

    beat_duration = _nearest_beat_duration(
        audio.beats_s,
        timeline_cursor_s,
        desired_duration,
        max_duration,
    )
    return round(beat_duration, 3)


def _audio_energy_at(audio: AudioAnalysis, timeline_s: float) -> float:
    if not audio.energy:
        return 0.2
    if audio.duration_s <= 0:
        return audio.energy[0]
    ratio = max(0.0, min(1.0, timeline_s / audio.duration_s))
    index = min(len(audio.energy) - 1, int(round(ratio * (len(audio.energy) - 1))))
    return audio.energy[index]


def _nearest_beat_duration(
    beats_s: list[float],
    timeline_cursor_s: float,
    desired_duration_s: float,
    max_duration_s: float,
) -> float:
    if max_duration_s <= 1.5:
        return max_duration_s

    min_duration_s = min(1.5, max_duration_s)
    beat_durations = [
        beat_s - timeline_cursor_s
        for beat_s in beats_s
        if min_duration_s <= beat_s - timeline_cursor_s <= max_duration_s
    ]
    if not beat_durations:
        return min(desired_duration_s, max_duration_s)
    return min(beat_durations, key=lambda duration_s: abs(duration_s - desired_duration_s))
