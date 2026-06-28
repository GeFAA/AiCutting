from pydantic import BaseModel, Field

# Energy-band thresholds on the 0..1 energy scale, shared by the beat analysis (section labels /
# cut density) and the rhythm grid (span / accent) so both classify "peak" and "build" the same way.
PEAK_ENERGY = 0.72  # at or above -> a drop/peak: shortest spans, accents, hard cuts
BUILD_ENERGY = 0.45  # at or above (but below peak) -> a build: mid-length spans


class BeatSection(BaseModel):
    label: str
    start_s: float = Field(ge=0)
    end_s: float = Field(gt=0)
    energy: float = Field(ge=0, le=1)
    cut_density: float = Field(ge=0, le=1)


class BeatPlan(BaseModel):
    beats_s: list[float]
    energy_curve: list[float]
    sections: list[BeatSection]
