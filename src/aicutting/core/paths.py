from dataclasses import dataclass
from pathlib import Path

from aicutting.core.errors import ValidationError


@dataclass(frozen=True)
class CutInputs:
    input_dir: Path
    music_path: Path | None
    output_dir: Path


def resolve_cut_inputs(input_dir: Path, music_path: Path | None, output_dir: Path) -> CutInputs:
    input_dir = input_dir.expanduser()
    music_path = music_path.expanduser() if music_path is not None else None
    output_dir = output_dir.expanduser()

    if not input_dir.exists():
        raise ValidationError(f"Input folder does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise ValidationError(f"Input path must be a folder: {input_dir}")
    if music_path is not None and not music_path.exists():
        raise ValidationError(f"Music path does not exist: {music_path}")

    return CutInputs(input_dir=input_dir, music_path=music_path, output_dir=output_dir)
