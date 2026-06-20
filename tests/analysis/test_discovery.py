from pathlib import Path

import pytest

from aicutting.analysis.discovery import discover_music, discover_videos
from aicutting.core.errors import ValidationError


def test_discover_videos_returns_supported_files_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.MP4").write_text("", encoding="utf-8")
    (tmp_path / "a.mov").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")

    assert discover_videos(tmp_path) == [tmp_path / "a.mov", tmp_path / "b.MP4"]


def test_discover_music_accepts_single_file(tmp_path: Path) -> None:
    song = tmp_path / "track.wav"
    song.write_text("", encoding="utf-8")

    assert discover_music(song) == song


def test_discover_videos_missing_folder_raises_validation_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    with pytest.raises(ValidationError, match="Video input folder does not exist"):
        discover_videos(missing)


def test_discover_videos_file_path_raises_validation_error(tmp_path: Path) -> None:
    video_input = tmp_path / "clip.mp4"
    video_input.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError, match="Video input path must be a folder"):
        discover_videos(video_input)


def test_discover_videos_empty_folder_raises_validation_error(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="No supported video files found"):
        discover_videos(tmp_path)


def test_discover_music_directory_chooses_first_supported_track(tmp_path: Path) -> None:
    (tmp_path / "b.mp3").write_text("", encoding="utf-8")
    (tmp_path / "a.flac").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")

    assert discover_music(tmp_path) == tmp_path / "a.flac"


def test_discover_music_unsupported_path_raises_validation_error(tmp_path: Path) -> None:
    notes = tmp_path / "notes.txt"
    notes.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError, match="No supported music file found"):
        discover_music(notes)
