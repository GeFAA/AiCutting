from pathlib import Path

from aicutting.core.models import AnalysisReport, AudioAnalysis, ClipCandidate, MediaAsset
from aicutting.planning.engine import build_cut_plan


def test_build_cut_plan_creates_timeline_until_target_duration() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("a.mp4"), duration_s=40, width=1920, height=1080, fps=25)],
        candidates=[
            ClipCandidate(
                asset_path=Path("a.mp4"),
                start_s=0,
                end_s=5,
                quality_score=0.9,
                motion_score=0.2,
                diversity_key="a",
            ),
            ClipCandidate(
                asset_path=Path("a.mp4"),
                start_s=5,
                end_s=10,
                quality_score=0.8,
                motion_score=0.4,
                diversity_key="b",
            ),
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )

    plan = build_cut_plan(report)

    assert plan.style == "adaptive_clean_cinematic"
    assert plan.timeline.clips[0].timeline_start_s == 0.0
    assert len(plan.timeline.clips) == 2


def test_build_cut_plan_uses_high_music_energy_for_shorter_cuts() -> None:
    candidates = [
        ClipCandidate(
            asset_path=Path(f"clip-{index}.mp4"),
            start_s=10.0,
            end_s=18.0,
            quality_score=0.8,
            motion_score=0.7,
            diversity_key=f"clip-{index}:1",
        )
        for index in range(8)
    ]
    report = AnalysisReport(
        media=[
            MediaAsset(
                path=Path("clip-0.mp4"),
                duration_s=80.0,
                width=3840,
                height=2160,
                fps=60.0,
            )
        ],
        candidates=candidates,
        audio=AudioAnalysis(
            path=Path("song.mp3"),
            duration_s=80.0,
            beats_s=[float(index) * 0.5 for index in range(160)],
            energy=[0.9 for _ in range(160)],
        ),
    )

    plan = build_cut_plan(report)

    assert len(plan.timeline.clips) >= 3
    assert max(clip.source_duration_s for clip in plan.timeline.clips[:3]) <= 4.0
