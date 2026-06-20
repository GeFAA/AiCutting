from pathlib import Path

import pytest

from aicutting.core.errors import ValidationError
from aicutting.core.paths import CutInputs, resolve_cut_inputs


def test_resolve_cut_inputs_accepts_existing_video_folder(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    music_dir = tmp_path / "music"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    music_dir.mkdir()

    result = resolve_cut_inputs(input_dir, music_dir, output_dir)

    assert result == CutInputs(input_dir=input_dir, music_path=music_dir, output_dir=output_dir)


def test_resolve_cut_inputs_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Input folder does not exist"):
        resolve_cut_inputs(tmp_path / "missing", None, tmp_path / "out")
