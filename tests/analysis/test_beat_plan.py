from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import AudioAnalysis


def test_build_beat_plan_groups_energy_sections() -> None:
    audio = AudioAnalysis(
        path=None,
        duration_s=12.0,
        beats_s=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        energy=[0.1, 0.2, 0.6, 0.9, 0.85, 0.5, 0.2, 0.1],
    )

    plan = build_beat_plan(audio)

    assert any(section.label == "peak" for section in plan.sections)
    assert max(section.cut_density for section in plan.sections) > 0.6


def test_build_beat_plan_handles_no_music() -> None:
    plan = build_beat_plan(AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[]))

    assert plan.beats_s == []
    assert plan.sections[0].label == "visual_default"
    assert plan.sections[0].cut_density == 0.35
