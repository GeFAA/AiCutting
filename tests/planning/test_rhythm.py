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


def test_grid_snaps_cuts_to_downbeats() -> None:
    # Every cut should land on a downbeat (every 4th beat) so it hits a strong beat.
    beats = [i * 0.5 for i in range(64)]  # 32 s; downbeats at i % 4 == 0
    audio = AudioAnalysis(path=None, duration_s=32.0, beats_s=beats, energy=[0.5])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=32.0)

    downbeats = {round(beats[i], 3) for i in range(0, len(beats), 4)}
    assert all(round(slot.start_s, 3) in downbeats for slot in grid)


def test_grid_covers_beatless_intro_so_time_stays_absolute() -> None:
    # The song's first beat is at ~9.7 s. The grid must start at 0 (covering the intro) so the
    # assembled timeline's cumulative time equals absolute song time and later cuts land on beats.
    beats = [9.71 + i * 0.47 for i in range(40)]
    audio = AudioAnalysis(path=None, duration_s=40.0, beats_s=beats, energy=[0.5])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=40.0)

    assert grid[0].start_s == 0.0
    assert any(abs(slot.start_s - 9.71) < 0.01 for slot in grid)  # a boundary on the first beat
    assert all(grid[i].end_s == grid[i + 1].start_s for i in range(len(grid) - 1))


def test_grid_covers_a_small_lead_in_so_cuts_stay_on_beat() -> None:
    # The song's first beat is at 0.26 s -- too small for an intro slot, but the lead-in must still
    # be covered so the cumulative timeline stays aligned with the music. Otherwise every cut is
    # offset from its beat by ~0.26 s (the bug that graded a real cut F on on-beat).
    beats = [round(0.26 + i * 0.68, 3) for i in range(60)]  # ~40 s, first beat at 0.26
    audio = AudioAnalysis(path=None, duration_s=42.0, beats_s=beats, energy=[0.5])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=42.0)

    assert grid[0].start_s == 0.0  # the first slot covers t=0, not the first beat
    # the cumulative slot durations (= the rendered cut times) all land on a beat
    cumulative = 0.0
    cut_times: list[float] = []
    for slot in grid:
        cumulative += slot.duration_s
        cut_times.append(round(cumulative, 3))
    for cut in cut_times[:-1]:  # the final partial slot may run a touch past the last beat
        assert min(abs(cut - beat) for beat in beats) <= 0.12, f"cut {cut} is off the beat"


def test_no_music_uses_default_visual_grid() -> None:
    audio = AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])
    grid = build_rhythm_grid(build_beat_plan(audio), target_duration_s=12.0)

    assert grid[0].start_s == 0.0
    assert grid[-1].end_s <= 12.0
    assert all(2.0 <= slot.duration_s <= 3.0 for slot in grid)
