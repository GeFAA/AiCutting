from pathlib import Path

from aicutting.core.models import ClipCandidate
from aicutting.planning.ranking import rank_candidates


def test_rank_candidates_prefers_score_and_diversity() -> None:
    candidates = [
        ClipCandidate(
            asset_path=Path("a.mp4"),
            start_s=0,
            end_s=4,
            quality_score=0.9,
            motion_score=0.4,
            diversity_key="lake",
        ),
        ClipCandidate(
            asset_path=Path("b.mp4"),
            start_s=0,
            end_s=4,
            quality_score=0.8,
            motion_score=0.8,
            diversity_key="forest",
        ),
        ClipCandidate(
            asset_path=Path("c.mp4"),
            start_s=0,
            end_s=4,
            quality_score=0.95,
            motion_score=0.1,
            diversity_key="lake",
        ),
    ]

    ranked = rank_candidates(candidates)

    assert ranked[0].diversity_key == "forest"
    assert ranked[1].diversity_key == "lake"


def test_rank_candidates_uses_composite_score_before_quality_score() -> None:
    high_quality_low_motion = ClipCandidate(
        asset_path=Path("quality.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.95,
        motion_score=0.0,
        diversity_key="quality",
    )
    lower_quality_high_motion = ClipCandidate(
        asset_path=Path("motion.mp4"),
        start_s=0,
        end_s=4,
        quality_score=0.8,
        motion_score=1.0,
        diversity_key="motion",
    )

    ranked = rank_candidates([high_quality_low_motion, lower_quality_high_motion])

    assert ranked[0] == lower_quality_high_motion


def test_rank_candidates_interleaves_source_assets() -> None:
    candidates = [
        ClipCandidate(
            asset_path=Path("a.mp4"),
            start_s=float(index * 5),
            end_s=float(index * 5 + 5),
            quality_score=0.9,
            motion_score=0.8 - (index * 0.02),
            diversity_key=f"a:{index}",
        )
        for index in range(4)
    ] + [
        ClipCandidate(
            asset_path=Path("b.mp4"),
            start_s=float(index * 5),
            end_s=float(index * 5 + 5),
            quality_score=0.82,
            motion_score=0.7 - (index * 0.02),
            diversity_key=f"b:{index}",
        )
        for index in range(2)
    ]

    ranked = rank_candidates(candidates)

    assert [candidate.asset_path.name for candidate in ranked[:4]] == [
        "a.mp4",
        "b.mp4",
        "a.mp4",
        "b.mp4",
    ]


def test_rank_candidates_prefers_usability_when_available() -> None:
    technically_clean_but_bad_motion = ClipCandidate(
        asset_path=Path("clean.mp4"),
        start_s=0,
        end_s=5,
        quality_score=0.95,
        motion_score=0.2,
        diversity_key="clean:0",
        usability_score=0.25,
    )
    usable_drone_move = ClipCandidate(
        asset_path=Path("usable.mp4"),
        start_s=10,
        end_s=15,
        quality_score=0.75,
        motion_score=0.6,
        diversity_key="usable:1",
        usability_score=0.92,
    )

    ranked = rank_candidates([technically_clean_but_bad_motion, usable_drone_move])

    assert ranked[0] == usable_drone_move
