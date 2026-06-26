from pathlib import Path

import pytest

from aicutting.core.models import (
    AnalysisReport,
    AudioAnalysis,
    ClipCandidate,
    DroneShotType,
    MediaAsset,
    Timeline,
    TimelineClip,
    Transition,
    TransitionType,
)


def test_timeline_model_round_trips() -> None:
    asset = MediaAsset(path=Path("clip.mp4"), duration_s=12.0, width=3840, height=2160, fps=25.0)
    clip = TimelineClip(
        asset_path=asset.path,
        source_start_s=1.0,
        source_end_s=5.0,
        timeline_start_s=0.0,
        transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
        speed=1.0,
        color_intent="neutral",
    )
    timeline = Timeline(target_duration_s=4.0, clips=[clip], fps=25.0, width=3840, height=2160)

    payload = timeline.model_dump(mode="json")
    restored = Timeline.model_validate(payload)

    assert restored.clips[0].asset_path == Path("clip.mp4")
    assert restored.target_duration_s == 4.0


def test_analysis_report_exposes_best_candidates() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("a.mp4"), duration_s=10.0, width=1920, height=1080, fps=25.0)],
        candidates=[
            ClipCandidate(
                asset_path=Path("a.mp4"),
                start_s=0.0,
                end_s=3.0,
                quality_score=0.8,
                motion_score=0.4,
                diversity_key="lake",
            ),
            ClipCandidate(
                asset_path=Path("a.mp4"),
                start_s=3.0,
                end_s=6.0,
                quality_score=0.4,
                motion_score=0.9,
                diversity_key="lake",
            ),
        ],
        audio=AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[]),
    )

    assert report.best_candidates(limit=1)[0].quality_score == 0.8


def test_clip_candidate_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="end_s must be greater than start_s"):
        ClipCandidate(
            asset_path=Path("a.mp4"),
            start_s=3.0,
            end_s=3.0,
            quality_score=0.8,
            motion_score=0.4,
            diversity_key="lake",
        )


def test_clip_candidate_exposes_drone_director_score() -> None:
    candidate = ClipCandidate(
        asset_path=Path("clip.mp4"),
        start_s=2.0,
        end_s=7.0,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key="clip:0",
        shot_type=DroneShotType.REVEAL,
        technical_score=0.75,
        motion_intent_score=0.9,
        reveal_score=0.85,
        novelty_score=0.6,
        drone_director_score=0.88,
    )

    assert candidate.shot_type == DroneShotType.REVEAL
    assert candidate.director_score == 0.88


def test_timeline_clip_rejects_source_end_before_source_start() -> None:
    with pytest.raises(ValueError, match="source_end_s must be greater than source_start_s"):
        TimelineClip(
            asset_path=Path("a.mp4"),
            source_start_s=5.0,
            source_end_s=5.0,
            timeline_start_s=0.0,
            transition_in=Transition(kind=TransitionType.HARD_CUT, duration_s=0.0),
            speed=1.0,
            color_intent="neutral",
        )


def test_analysis_report_rejects_negative_best_candidate_limit() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("a.mp4"), duration_s=10.0, width=1920, height=1080, fps=25.0)],
        candidates=[],
        audio=AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[]),
    )

    with pytest.raises(ValueError, match="limit must be non-negative"):
        report.best_candidates(limit=-1)
