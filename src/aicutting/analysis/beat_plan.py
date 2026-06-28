from aicutting.core.models import AudioAnalysis
from aicutting.director.drone_models import BUILD_ENERGY, PEAK_ENERGY, BeatPlan, BeatSection


def build_beat_plan(audio: AudioAnalysis) -> BeatPlan:
    if not audio.beats_s:
        return BeatPlan(
            beats_s=[],
            energy_curve=[],
            sections=[
                BeatSection(
                    label="visual_default",
                    start_s=0.0,
                    end_s=max(audio.duration_s, 1.0),
                    energy=0.2,
                    cut_density=0.35,
                )
            ],
        )

    return BeatPlan(
        beats_s=audio.beats_s,
        energy_curve=audio.energy,
        sections=_sections(audio),
    )


def _sections(audio: AudioAnalysis) -> list[BeatSection]:
    if not audio.energy:
        return [
            BeatSection(
                label="steady",
                start_s=0.0,
                end_s=max(audio.duration_s, 1.0),
                energy=0.35,
                cut_density=0.4,
            )
        ]
    section_count = min(4, max(1, len(audio.energy)))
    chunk_size = max(1, len(audio.energy) // section_count)
    sections: list[BeatSection] = []
    for index in range(section_count):
        start_i = index * chunk_size
        end_i = (
            len(audio.energy)
            if index == section_count - 1
            else min(len(audio.energy), (index + 1) * chunk_size)
        )
        values = audio.energy[start_i:end_i]
        avg = sum(values) / len(values)
        label = _label(avg, index, section_count)
        start_s = round((start_i / len(audio.energy)) * max(audio.duration_s, 0.0), 3)
        end_s = round((end_i / len(audio.energy)) * max(audio.duration_s, 0.0), 3)
        sections.append(
            BeatSection(
                label=label,
                start_s=start_s,
                end_s=max(end_s, start_s + 0.001),
                energy=round(avg, 6),
                cut_density=round(_cut_density(avg), 6),
            )
        )
    return sections


def _label(energy: float, index: int, section_count: int) -> str:
    if energy >= PEAK_ENERGY:
        return "peak"
    if index == 0:
        return "intro"
    if index == section_count - 1:
        return "release"
    if energy >= BUILD_ENERGY:
        return "build"
    return "calm"


def _cut_density(energy: float) -> float:
    if energy >= PEAK_ENERGY:
        return 0.85
    if energy >= BUILD_ENERGY:
        return 0.6
    return 0.35
