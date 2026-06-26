from pathlib import Path

from aicutting.core.models import DroneShotType, TransitionType
from aicutting.director.drone_models import (
    BeatPlan,
    BeatSection,
    EffectDecision,
    EffectPlan,
    ShotCandidateArtifact,
    StoryPlan,
    StoryPlanClip,
)


def test_shot_candidate_artifact_records_drone_reasoning() -> None:
    artifact = ShotCandidateArtifact(
        asset_path=Path("clip.mp4"),
        start_s=3.0,
        end_s=8.0,
        shot_type=DroneShotType.REVEAL,
        selected=True,
        rejected=False,
        rejection_reason=None,
        technical_score=0.8,
        stability_score=0.9,
        composition_score=0.75,
        motion_intent_score=0.86,
        reveal_score=0.91,
        novelty_score=0.6,
        drone_director_score=0.87,
        reasons=["smooth reveal", "strong stability"],
    )

    assert artifact.duration_s == 5.0
    assert artifact.reasons[0] == "smooth reveal"


def test_beat_story_and_effect_models_are_serializable() -> None:
    beat_plan = BeatPlan(
        beats_s=[0.0, 1.0, 2.0],
        downbeats_s=[0.0, 2.0],
        phrase_boundaries_s=[0.0, 4.0],
        energy_curve=[0.2, 0.8],
        sections=[BeatSection(label="peak", start_s=1.0, end_s=3.0, energy=0.8, cut_density=0.8)],
    )
    story = StoryPlan(
        target_duration_s=12.0,
        clips=[
            StoryPlanClip(
                asset_path=Path("clip.mp4"),
                source_start_s=3.0,
                source_end_s=7.0,
                role="peak",
                shot_type=DroneShotType.REVEAL,
                beat_anchor_s=4.0,
                reason="best reveal at peak",
            )
        ],
    )
    effects = EffectPlan(
        decisions=[
            EffectDecision(
                clip_index=0,
                transition=TransitionType.SMOOTH_ZOOM,
                duration_s=0.25,
                confidence=0.86,
                beat_anchor_s=4.0,
                reason="approach motion at peak",
            )
        ]
    )

    assert beat_plan.sections[0].label == "peak"
    assert story.clips[0].role == "peak"
    assert effects.decisions[0].transition == TransitionType.SMOOTH_ZOOM
