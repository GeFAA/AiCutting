from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from aicutting.core.models import DroneShotType, TransitionType


class FootageMoment(BaseModel):
    moment_id: str
    asset_path: Path
    timestamp_s: float = Field(ge=0)


class ContactSheet(BaseModel):
    path: Path
    moment_ids: list[str]


class MomentRating(BaseModel):
    moment_id: str
    cinematic_score: float = Field(ge=0, le=1)
    shot_type: DroneShotType
    keep: bool
    reason: str


class RhythmSlot(BaseModel):
    index: int = Field(ge=0)
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    energy: float = Field(ge=0, le=1)
    is_accent: bool
    section: str

    @field_validator("end_s")
    @classmethod
    def end_after_start(cls, value: float, info: ValidationInfo) -> float:
        if value <= info.data.get("start_s", 0.0):
            raise ValueError("end_s must be greater than start_s")
        return value

    @property
    def duration_s(self) -> float:
        return round(self.end_s - self.start_s, 6)


class EditClip(BaseModel):
    slot_index: int = Field(ge=0)
    moment_id: str
    effect: TransitionType
    reason: str


class EditDecision(BaseModel):
    arc: str
    clips: list[EditClip]


class Director3Report(BaseModel):
    used_agent: bool
    backend: str | None
    rated_moments: int = Field(ge=0)
    kept_moments: int = Field(ge=0)
    timeline_clips: int = Field(ge=0)
    warnings: list[str]
