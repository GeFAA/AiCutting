from pathlib import Path

from aicutting.core.models import ClipCandidate, LocationTitle
from aicutting.director.models import DirectorDecision, DirectorReport, LocationSuggestion


def test_clip_candidate_accepts_motion_scores_and_rejection_reason() -> None:
    candidate = ClipCandidate(
        asset_path=Path("clip.mp4"),
        start_s=12.0,
        end_s=17.0,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key="clip:1",
        smoothness_score=0.9,
        jitter_score=0.05,
        movement_score=0.85,
        composition_score=0.75,
        usability_score=0.88,
        movement_type="push_in",
        rejection_reason=None,
    )

    assert candidate.usability_score == 0.88
    assert candidate.movement_type == "push_in"
    assert candidate.director_score > candidate.composite_score


def test_director_report_serializes_selected_and_rejected_segments() -> None:
    decision = DirectorDecision(
        asset_path=Path("clip.mp4"),
        start_s=12.0,
        end_s=17.0,
        selected=True,
        reason="smooth push-in near beat",
        score=0.91,
    )
    report = DirectorReport(
        decisions=[decision],
        warnings=[],
        title=LocationTitle(title="Madeira Coast", subtitle="Portugal", confidence=0.86),
    )

    payload = report.model_dump(mode="json")

    assert payload["decisions"][0]["selected"] is True
    assert payload["title"]["title"] == "Madeira Coast"


def test_location_suggestion_requires_confidence_gate() -> None:
    suggestion = LocationSuggestion(
        title="Unknown beach",
        place="unknown",
        confidence=0.42,
        evidence=["agent saw coastline"],
        should_render=True,
    )

    assert suggestion.renderable is False
