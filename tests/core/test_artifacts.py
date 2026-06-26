from pathlib import Path

from aicutting.core.artifacts import read_json_model, write_json_model
from aicutting.core.models import AudioAnalysis


def test_write_and_read_json_model(tmp_path: Path) -> None:
    artifact = tmp_path / "audio.json"
    model = AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])

    write_json_model(artifact, model)
    restored = read_json_model(artifact, AudioAnalysis)

    assert restored == model
    assert artifact.read_text(encoding="utf-8").endswith("\n")


def test_write_json_model_uses_indented_sorted_keys(tmp_path: Path) -> None:
    artifact = tmp_path / "audio.json"
    model = AudioAnalysis(path=None, duration_s=0.0, beats_s=[], energy=[])

    write_json_model(artifact, model)
    raw = artifact.read_text(encoding="utf-8")

    assert '  "beats_s": []' in raw
    assert (
        raw.index('"beats_s"')
        < raw.index('"duration_s"')
        < raw.index('"energy"')
        < raw.index('"path"')
    )
