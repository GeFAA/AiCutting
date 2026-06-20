from pathlib import Path

from aicutting.analysis.discovery import discover_music, discover_videos


def test_discover_videos_returns_supported_files_sorted(tmp_path: Path) -> None:
    (tmp_path / "b.MP4").write_text("", encoding="utf-8")
    (tmp_path / "a.mov").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")

    assert discover_videos(tmp_path) == [tmp_path / "a.mov", tmp_path / "b.MP4"]


def test_discover_music_accepts_single_file(tmp_path: Path) -> None:
    song = tmp_path / "track.wav"
    song.write_text("", encoding="utf-8")

    assert discover_music(song) == song
