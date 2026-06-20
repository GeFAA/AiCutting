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
