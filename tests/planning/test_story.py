from pathlib import Path

from aicutting.core.models import ClipCandidate, DroneShotType
from aicutting.director.drone_models import BeatPlan, BeatSection
from aicutting.planning.story import build_story_plan


def _candidate(start: float, shot_type: DroneShotType, score: float) -> ClipCandidate:
    return ClipCandidate(
        asset_path=Path(f"{shot_type.value}-{start}.mp4"),
        start_s=start,
        end_s=start + 5.0,
        quality_score=0.8,
        motion_score=0.7,
        diversity_key=f"{shot_type.value}:{start}",
        shot_type=shot_type,
        drone_director_score=score,
    )


def test_story_plan_prefers_drone_edit_arc() -> None:
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0, 4.0, 6.0, 8.0],
        downbeats_s=[0.0, 4.0, 8.0],
        phrase_boundaries_s=[0.0, 8.0],
        energy_curve=[0.2, 0.8],
        sections=[BeatSection(label="peak", start_s=0.0, end_s=10.0, energy=0.8, cut_density=0.85)],
    )
    candidates = [
        _candidate(0.0, DroneShotType.SEARCH_MOTION, 0.2),
        _candidate(5.0, DroneShotType.ESTABLISHING, 0.75),
        _candidate(10.0, DroneShotType.APPROACH, 0.8),
        _candidate(15.0, DroneShotType.REVEAL, 0.95),
        _candidate(20.0, DroneShotType.PULL_BACK, 0.76),
    ]

    plan = build_story_plan(candidates, beat_plan, target_duration_s=14.0)

    assert [clip.role for clip in plan.clips] == ["establish", "move", "peak", "release"]
    assert plan.clips[2].shot_type == DroneShotType.REVEAL
    assert plan.clips[2].beat_anchor_s in beat_plan.downbeats_s
    assert all(clip.shot_type != DroneShotType.SEARCH_MOTION for clip in plan.clips)
