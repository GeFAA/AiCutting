from pathlib import Path

from aicutting.core.errors import ValidationError

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac"}


def discover_videos(input_dir: Path) -> list[Path]:
    if not input_dir.exists():
        raise ValidationError(f"Video input folder does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise ValidationError(f"Video input path must be a folder: {input_dir}")

    videos = sorted(
        path
        for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        raise ValidationError(f"No supported video files found in {input_dir}")
    return videos


def discover_music(music_path: Path | None) -> Path | None:
    if music_path is None:
        return None
    if music_path.is_file() and music_path.suffix.lower() in AUDIO_EXTENSIONS:
        return music_path
    if music_path.is_dir():
        tracks = sorted(
            path
            for path in music_path.iterdir()
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        )
        if tracks:
            return tracks[0]
    raise ValidationError(f"No supported music file found at {music_path}")
