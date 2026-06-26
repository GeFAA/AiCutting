from pathlib import Path

from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.drone_models import BeatPlan, BeatSection, StoryPlan, StoryPlanClip
from aicutting.planning.effects import build_effect_plan


def _clip(index: int, shot_type: DroneShotType, role: str) -> StoryPlanClip:
    return StoryPlanClip(
        asset_path=Path(f"clip-{index}.mp4"),
        source_start_s=float(index * 5),
        source_end_s=float(index * 5 + 4),
        role=role,
        shot_type=shot_type,
        beat_anchor_s=float(index * 2),
        reason=role,
    )


def test_effect_plan_uses_zoom_for_approach_peak() -> None:
    story = StoryPlan(
        target_duration_s=12.0,
        clips=[
            _clip(0, DroneShotType.ESTABLISHING, "establish"),
            _clip(1, DroneShotType.APPROACH, "move"),
            _clip(2, DroneShotType.REVEAL, "peak"),
        ],
    )
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0, 4.0],
        downbeats_s=[0.0, 4.0],
        phrase_boundaries_s=[0.0],
        energy_curve=[0.2, 0.9],
        sections=[BeatSection(label="peak", start_s=0.0, end_s=8.0, energy=0.9, cut_density=0.9)],
    )

    plan = build_effect_plan(story, beat_plan)

    assert plan.decisions[1].transition == TransitionType.SMOOTH_ZOOM
    assert plan.decisions[1].confidence >= 0.75


def test_effect_plan_keeps_calm_establishing_as_dissolve() -> None:
    story = StoryPlan(
        target_duration_s=10.0,
        clips=[
            _clip(0, DroneShotType.ESTABLISHING, "establish"),
            _clip(1, DroneShotType.PULL_BACK, "release"),
        ],
    )
    beat_plan = BeatPlan(
        beats_s=[0.0, 2.0],
        downbeats_s=[0.0],
        phrase_boundaries_s=[0.0],
        energy_curve=[0.2],
        sections=[BeatSection(label="calm", start_s=0.0, end_s=8.0, energy=0.2, cut_density=0.35)],
    )

    plan = build_effect_plan(story, beat_plan)

    assert plan.decisions[1].transition == TransitionType.DISSOLVE
