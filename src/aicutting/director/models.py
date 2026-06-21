from pathlib import Path

from pydantic import BaseModel, Field

from aicutting.core.models import LocationTitle


class DirectorDecision(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    selected: bool
    reason: str
    score: float = Field(ge=0, le=1)


class RejectedSegment(BaseModel):
    asset_path: Path
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    reason: str
    score: float = Field(ge=0, le=1)


class LocationSuggestion(BaseModel):
    title: str
    place: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[str]
    should_render: bool

    @property
    def renderable(self) -> bool:
        return self.should_render and self.confidence >= 0.75


class DirectorReport(BaseModel):
    decisions: list[DirectorDecision]
    warnings: list[str]
    title: LocationTitle | None = None
