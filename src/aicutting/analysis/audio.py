from collections.abc import Callable
from pathlib import Path

import librosa
import numpy as np

from aicutting.core.models import AudioAnalysis

AudioLoader = Callable[[Path], tuple[list[float], float, list[float]]]


def analyze_music(path: Path | None, loader: AudioLoader | None = None) -> AudioAnalysis:
    if path is None:
        return AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])
    beats_s, duration_s, energy = loader(path) if loader else _load_with_librosa(path)
    return AudioAnalysis(path=path, duration_s=duration_s, beats_s=beats_s, energy=energy)


def _load_with_librosa(path: Path) -> tuple[list[float], float, list[float]]:
    y, sr = librosa.load(path, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    del tempo
    beats_s = librosa.frames_to_time(beat_frames, sr=sr).round(3).tolist()
    duration_s = float(librosa.get_duration(y=y, sr=sr))
    rms = librosa.feature.rms(y=y)[0]
    energy = np.interp(rms, (float(rms.min()), float(rms.max()) or 1.0), (0.0, 1.0)).round(
        6
    ).tolist()
    return beats_s, round(duration_s, 3), energy
