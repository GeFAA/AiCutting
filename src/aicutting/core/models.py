from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class MediaAsset(BaseModel):
    path: Path
    duration_s: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)


class AudioAnalysis(BaseModel):
    path: Path | None
    duration_s: float = Field(ge=0)
    beats_s: list[float]
    energy: list[float]


class LocationTitle(BaseModel):
    title: str
    subtitle: str | None = None
    confidence: float = Field(ge=0, le=1)


class ClipCandidate(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    quality_score: float = Field(ge=0, le=1)
    motion_score: float = Field(ge=0, le=1)
    diversity_key: str
    smoothness_score: float | None = Field(default=None, ge=0, le=1)
    jitter_score: float | None = Field(default=None, ge=0, le=1)
    movement_score: float | None = Field(default=None, ge=0, le=1)
    composition_score: float | None = Field(default=None, ge=0, le=1)
    usability_score: float | None = Field(default=None, ge=0, le=1)
    movement_type: str = "unknown"
    rejection_reason: str | None = None

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

    @property
    def composite_score(self) -> float:
        return round((self.quality_score * 0.7) + (self.motion_score * 0.3), 6)

    @property
    def director_score(self) -> float:
        usability = (
            self.usability_score if self.usability_score is not None else self.composite_score
        )
        return round((self.composite_score * 0.35) + (usability * 0.65), 6)


class AnalysisReport(BaseModel):
    media: list[MediaAsset]
    candidates: list[ClipCandidate]
    audio: AudioAnalysis

    def best_candidates(self, limit: int) -> list[ClipCandidate]:
        if limit < 0:
            raise ValueError("limit must be non-negative")
        return sorted(self.candidates, key=lambda item: item.composite_score, reverse=True)[:limit]


class TransitionType(StrEnum):
    HARD_CUT = "hard_cut"
    DISSOLVE = "dissolve"
    MATCH_CUT = "match_cut"


class Transition(BaseModel):
    kind: TransitionType
    duration_s: float = Field(ge=0)


class TimelineClip(BaseModel):
    asset_path: Path
    source_start_s: float = Field(ge=0)
    source_end_s: float = Field(gt=0)
    timeline_start_s: float = Field(ge=0)
    transition_in: Transition
    speed: float = Field(gt=0)
    color_intent: str

    @field_validator("source_end_s")
    @classmethod
    def source_end_must_follow_source_start(cls, value: float, info: ValidationInfo) -> float:
        start = info.data.get("source_start_s", 0.0)
        if value <= start:
            raise ValueError("source_end_s must be greater than source_start_s")
        return value

    @property
    def source_duration_s(self) -> float:
        return self.source_end_s - self.source_start_s

    @property
    def timeline_duration_s(self) -> float:
        return self.source_duration_s / self.speed


class Timeline(BaseModel):
    target_duration_s: float = Field(gt=0)
    clips: list[TimelineClip]
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class CutPlan(BaseModel):
    target_duration_s: float = Field(gt=0)
    style: str
    timeline: Timeline
    notes: list[str]
