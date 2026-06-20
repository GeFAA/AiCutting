from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from aicutting.analysis.discovery import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS


class JobStatus(StrEnum):
    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"


class Preset(StrEnum):
    CINEMATIC_AUTO = "cinematic_auto"

    @property
    def label(self) -> str:
        return "Cinematic Auto"


@dataclass(frozen=True)
class GuiSelection:
    input_dir: Path | None = None
    music_path: Path | None = None
    output_dir: Path | None = None
    preset: Preset = Preset.CINEMATIC_AUTO
    dry_run: bool = False


@dataclass(frozen=True)
class ValidationResult:
    status: JobStatus
    messages: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.status == JobStatus.READY


def default_output_dir(input_dir: Path) -> Path:
    return input_dir.parent / f"{input_dir.name}-aicutting-output"


def _contains_supported_file(folder: Path, extensions: set[str]) -> bool | None:
    try:
        return any(
            path.is_file() and path.suffix.lower() in extensions
            for path in folder.iterdir()
        )
    except OSError:
        return None


def validate_selection(selection: GuiSelection) -> ValidationResult:
    messages: list[str] = []
    if selection.input_dir is None:
        messages.append("Choose a folder with drone videos.")
    elif not selection.input_dir.exists():
        messages.append(f"Input folder does not exist: {selection.input_dir}")
    elif not selection.input_dir.is_dir():
        messages.append(f"Input path must be a folder: {selection.input_dir}")
    else:
        contains_video = _contains_supported_file(selection.input_dir, VIDEO_EXTENSIONS)
        if contains_video is None:
            messages.append(f"Unable to read folder: {selection.input_dir}")
        elif not contains_video:
            messages.append(f"No supported video files found in {selection.input_dir}")

    if selection.music_path is not None:
        if not selection.music_path.exists():
            messages.append(f"Music path does not exist: {selection.music_path}")
        elif (
            selection.music_path.is_file()
            and selection.music_path.suffix.lower() not in AUDIO_EXTENSIONS
        ):
            messages.append(f"Unsupported music file: {selection.music_path}")
        elif selection.music_path.is_dir():
            contains_music = _contains_supported_file(selection.music_path, AUDIO_EXTENSIONS)
            if contains_music is None:
                messages.append(f"Unable to read music folder: {selection.music_path}")
            elif not contains_music:
                messages.append(
                    f"No supported music file found at {selection.music_path}"
                )

    if selection.output_dir is None:
        messages.append("Choose an output folder.")
    elif selection.output_dir.exists() and not selection.output_dir.is_dir():
        messages.append(f"Output path must be a folder: {selection.output_dir}")

    return ValidationResult(
        status=JobStatus.READY if not messages else JobStatus.IDLE,
        messages=messages,
    )
