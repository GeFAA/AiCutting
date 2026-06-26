from aicutting.analysis.beat_plan import build_beat_plan
from aicutting.core.models import AudioAnalysis
from aicutting.planning.rhythm import build_rhythm_grid


def test_grid_fills_target_and_snaps_to_beats() -> None:
    beats = [i * 0.5 for i in range(0, 60)]  # 30 s of beats
    audio = AudioAnalysis(path=None, duration_s=30.0, beats_s=beats, energy=[0.2, 0.9, 0.3])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=30.0)

    assert grid, "expected slots"
    assert grid[0].start_s == 0.0
    assert grid[-1].end_s <= 30.0 + 0.5
    assert grid[-1].end_s >= 24.0  # fills most of the song
    assert all(slot.start_s < slot.end_s for slot in grid)
    assert all(grid[i].end_s == grid[i + 1].start_s for i in range(len(grid) - 1))


def test_high_energy_slots_are_shorter_than_calm_slots() -> None:
    beats = [i * 0.5 for i in range(0, 80)]
    calm = AudioAnalysis(path=None, duration_s=40.0, beats_s=beats, energy=[0.1])
    loud = AudioAnalysis(path=None, duration_s=40.0, beats_s=beats, energy=[0.95])
    calm_grid = build_rhythm_grid(build_beat_plan(calm), target_duration_s=40.0)
    loud_grid = build_rhythm_grid(build_beat_plan(loud), target_duration_s=40.0)

    assert len(loud_grid) > len(calm_grid)


def test_no_music_uses_default_visual_grid() -> None:
    audio = AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=12.0)

    assert grid[0].start_s == 0.0
    assert grid[-1].end_s <= 12.0
    assert all(2.0 <= slot.duration_s <= 3.0 for slot in grid)
