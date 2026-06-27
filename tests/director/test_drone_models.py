from aicutting.director.drone_models import BeatPlan, BeatSection


def test_beat_plan_is_serializable() -> None:
    beat_plan = BeatPlan(
        beats_s=[0.0, 1.0, 2.0],
        downbeats_s=[0.0, 2.0],
        phrase_boundaries_s=[0.0, 4.0],
        energy_curve=[0.2, 0.8],
        sections=[BeatSection(label="peak", start_s=1.0, end_s=3.0, energy=0.8, cut_density=0.8)],
    )

    assert beat_plan.sections[0].label == "peak"
    assert beat_plan.beats_s == [0.0, 1.0, 2.0]
