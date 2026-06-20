from pathlib import Path

from aicutting.analysis.audio import analyze_music


def test_analyze_music_none_returns_empty_audio() -> None:
    analysis = analyze_music(None)

    assert analysis.path is None
    assert analysis.duration_s == 0.0
    assert analysis.beats_s == []
    assert analysis.energy == []


def test_analyze_music_uses_injected_loader(tmp_path: Path) -> None:
    music = tmp_path / "track.wav"
    music.write_text("", encoding="utf-8")

    analysis = analyze_music(music, loader=lambda _: ([0.0, 1.0, 2.0], 3.0, [0.2, 0.9]))

    assert analysis.path == music
    assert analysis.duration_s == 3.0
    assert analysis.beats_s == [0.0, 1.0, 2.0]
    assert analysis.energy == [0.2, 0.9]
