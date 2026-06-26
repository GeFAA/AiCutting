from pathlib import Path

from aicutting.core.models import ClipCandidate, TransitionType
from aicutting.planning.transitions import choose_transition


def test_choose_transition_defaults_to_hard_cut() -> None:
    previous = ClipCandidate(
        asset_path=Path("a.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.3,
        diversity_key="a",
    )
    current = ClipCandidate(
        asset_path=Path("b.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.15,
        diversity_key="b",
    )

    assert choose_transition(previous, current, beat_energy=0.2).kind == TransitionType.HARD_CUT


def test_choose_transition_uses_dissolve_for_calm_related_motion() -> None:
    previous = ClipCandidate(
        asset_path=Path("a.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.2,
        diversity_key="a",
    )
    current = ClipCandidate(
        asset_path=Path("b.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.25,
        diversity_key="b",
    )

    transition = choose_transition(previous, current, beat_energy=0.1)

    assert transition.kind == TransitionType.DISSOLVE
    assert transition.duration_s == 0.35


def test_choose_transition_uses_dissolve_at_motion_delta_boundary() -> None:
    previous = ClipCandidate(
        asset_path=Path("a.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.2,
        diversity_key="a",
    )
    current = ClipCandidate(
        asset_path=Path("b.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.3,
        diversity_key="b",
    )

    transition = choose_transition(previous, current, beat_energy=0.1)

    assert transition.kind == TransitionType.DISSOLVE
    assert transition.duration_s == 0.35


def test_legacy_transition_chooser_still_returns_basic_transition() -> None:
    previous = ClipCandidate(
        asset_path=Path("a.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.3,
        diversity_key="a",
    )
    current = ClipCandidate(
        asset_path=Path("b.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=0.32,
        diversity_key="b",
    )

    transition = choose_transition(previous=previous, current=current, beat_energy=0.2)

    assert transition.kind == TransitionType.DISSOLVE
