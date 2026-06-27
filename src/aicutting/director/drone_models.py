from pydantic import BaseModel, Field


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
