import warnings
from pathlib import Path

import numpy as np
import pytest

from aicutting.analysis.audio import _normalize_energy, analyze_music
from aicutting.core.errors import ExternalToolError


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


def test_analyze_music_wraps_unreadable_audio_errors(tmp_path: Path) -> None:
    music = tmp_path / "broken.mp3"
    music.write_bytes(b"not really an mp3")

    def broken_loader(path: Path) -> tuple[list[float], float, list[float]]:
        raise RuntimeError("Giving up searching valid MPEG header")

    with pytest.raises(ExternalToolError, match="Could not analyze music file"):
        analyze_music(music, loader=broken_loader)


def test_analyze_music_suppresses_known_librosa_fallback_warnings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    music = tmp_path / "track.mp3"
    music.write_bytes(b"fake")

    def fake_load(path: Path, mono: bool) -> tuple[np.ndarray, int]:
        del path, mono
        warnings.warn("PySoundFile failed. Trying audioread instead.", UserWarning, stacklevel=2)
        return np.zeros(1024), 22050

    monkeypatch.setattr("aicutting.analysis.audio.librosa.load", fake_load)
    monkeypatch.setattr(
        "aicutting.analysis.audio.librosa.beat.beat_track",
        lambda y, sr: (120.0, np.array([], dtype=int)),
    )
    monkeypatch.setattr(
        "aicutting.analysis.audio.librosa.frames_to_time",
        lambda frames, sr: np.array([]),
    )
    monkeypatch.setattr(
        "aicutting.analysis.audio.librosa.get_duration",
        lambda y, sr: 1.0,
    )
    monkeypatch.setattr(
        "aicutting.analysis.audio.librosa.feature.rms",
        lambda y: np.array([[0.0]]),
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        analyze_music(music)

    assert caught == []


def test_normalize_energy_handles_constant_and_varying_rms() -> None:
    assert _normalize_energy(np.array([0.5, 0.5, 0.5])) == [0.0, 0.0, 0.0]

    energy = _normalize_energy(np.array([0.2, 0.5, 0.8]))

    assert min(energy) == 0.0
    assert max(energy) == 1.0
