from pathlib import Path

from aicutting.core.models import AnalysisReport, AudioAnalysis, ClipCandidate, MediaAsset
from aicutting.director.engine import build_director_outputs
from aicutting.director.models import LocationSuggestion


def _candidate(start: float, rejection: str | None = None, usability: float = 0.8) -> ClipCandidate:
    return ClipCandidate(
        asset_path=Path("clip.mp4"),
        start_s=start,
        end_s=start + 5,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key=f"clip:{int(start)}",
        usability_score=usability,
        movement_type="push_in" if rejection is None else "shaky",
        rejection_reason=rejection,
    )


def test_director_outputs_remove_rejected_segments_and_explain_them() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("clip.mp4"), duration_s=40, width=1920, height=1080, fps=25)],
        candidates=[
            _candidate(0, "takeoff_or_landing_motion", usability=0.1),
            _candidate(10, None, usability=0.9),
        ],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )

    outputs = build_director_outputs(report)

    assert [candidate.start_s for candidate in outputs.analysis.candidates] == [10]
    assert outputs.rejected_segments[0].reason == "takeoff_or_landing_motion"
    assert outputs.director_report.decisions[0].selected is True


def test_director_outputs_attach_high_confidence_title_to_plan_input() -> None:
    report = AnalysisReport(
        media=[MediaAsset(path=Path("clip.mp4"), duration_s=40, width=1920, height=1080, fps=25)],
        candidates=[_candidate(10, None, usability=0.9)],
        audio=AudioAnalysis(path=None, duration_s=0, beats_s=[], energy=[]),
    )
    suggestion = LocationSuggestion(
        title="Madeira Coast",
        place="Madeira, Portugal",
        confidence=0.86,
        evidence=["metadata GPS"],
        should_render=True,
    )

    outputs = build_director_outputs(report, location_suggestions=[suggestion])

    assert outputs.analysis.candidates[0].start_s == 10
    assert outputs.director_report.title is not None
    assert outputs.director_report.title.title == "Madeira Coast"
