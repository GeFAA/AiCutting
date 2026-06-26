from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from aicutting.core.models import DroneShotType, TransitionType


class ShotCandidateArtifact(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    shot_type: DroneShotType
    selected: bool
    rejected: bool
    rejection_reason: str | None
    technical_score: float = Field(ge=0, le=1)
    stability_score: float = Field(ge=0, le=1)
    composition_score: float = Field(ge=0, le=1)
    motion_intent_score: float = Field(ge=0, le=1)
    reveal_score: float = Field(ge=0, le=1)
    novelty_score: float = Field(ge=0, le=1)
    drone_director_score: float = Field(ge=0, le=1)
    reasons: list[str]

    @field_validator("end_s")
    @classmethod
    def end_must_follow_start(cls, value: float, info: ValidationInfo) -> float:
        start = info.data.get("start_s", 0.0)
        if value <= start:
            raise ValueError("end_s must be greater than start_s")
        return value

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s


class BeatSection(BaseModel):
    label: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    energy: float = Field(ge=0, le=1)
    cut_density: float = Field(ge=0, le=1)


class BeatPlan(BaseModel):
    beats_s: list[float]
    downbeats_s: list[float]
    phrase_boundaries_s: list[float]
    energy_curve: list[float]
    sections: list[BeatSection]


class StoryPlanClip(BaseModel):
    asset_path: Path
    source_start_s: float = Field(ge=0)
    source_end_s: float = Field(gt=0)
    role: str
    shot_type: DroneShotType
    beat_anchor_s: float | None = Field(default=None, ge=0)
    reason: str


class StoryPlan(BaseModel):
    target_duration_s: float = Field(gt=0)
    clips: list[StoryPlanClip]


class EffectDecision(BaseModel):
    clip_index: int = Field(ge=0)
    transition: TransitionType
    duration_s: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    beat_anchor_s: float | None = Field(default=None, ge=0)
    source_shot_type: DroneShotType | None = None
    target_shot_type: DroneShotType | None = None
    reason: str


class EffectPlan(BaseModel):
    decisions: list[EffectDecision]


class Director2Report(BaseModel):
    selected_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    average_drone_director_score: float = Field(ge=0, le=1)
    warnings: list[str]
