from pathlib import Path

from aicutting.gui.state import (
    GuiSelection,
    JobStatus,
    Preset,
    default_output_dir,
    validate_selection,
)


def test_default_output_dir_is_inside_source_parent(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()

    assert default_output_dir(source) == tmp_path / "drone-aicutting-output"


def test_selection_with_video_folder_and_output_is_ready(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    (source / "clip.mp4").write_text("", encoding="utf-8")
    output = tmp_path / "out"
    selection = GuiSelection(input_dir=source, music_path=None, output_dir=output)

    result = validate_selection(selection)

    assert result.ready is True
    assert result.status == JobStatus.READY
    assert result.messages == []


def test_selection_rejects_folder_without_supported_videos(tmp_path: Path) -> None:
    source = tmp_path / "empty"
    source.mkdir()
    output = tmp_path / "out"

    result = validate_selection(GuiSelection(input_dir=source, output_dir=output))

    assert result.ready is False
    assert result.status == JobStatus.IDLE
    assert "No supported video files found" in result.messages[0]


def test_selection_accepts_supported_music_file(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    (source / "clip.mov").write_text("", encoding="utf-8")
    music = tmp_path / "song.mp3"
    music.write_text("", encoding="utf-8")

    result = validate_selection(
        GuiSelection(
            input_dir=source,
            music_path=music,
            output_dir=tmp_path / "out",
            preset=Preset.CINEMATIC_AUTO,
        )
    )

    assert result.ready is True


def test_selection_rejects_output_path_that_is_file(tmp_path: Path) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    (source / "clip.mp4").write_text("", encoding="utf-8")
    output = tmp_path / "out.txt"
    output.write_text("", encoding="utf-8")

    result = validate_selection(GuiSelection(input_dir=source, output_dir=output))

    assert result.ready is False
    assert result.status == JobStatus.IDLE
    assert f"Output path must be a folder: {output}" in result.messages


def test_selection_reports_unreadable_input_folder(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    output = tmp_path / "out"
    original_iterdir = type(source).iterdir

    def unreadable_iterdir(path: Path):
        if path == source:
            raise OSError("access denied")
        return original_iterdir(path)

    monkeypatch.setattr(type(source), "iterdir", unreadable_iterdir)

    result = validate_selection(GuiSelection(input_dir=source, output_dir=output))

    assert result.ready is False
    assert result.status == JobStatus.IDLE
    assert f"Unable to read folder: {source}" in result.messages


def test_selection_reports_unreadable_music_folder(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "drone"
    source.mkdir()
    (source / "clip.mp4").write_text("", encoding="utf-8")
    music = tmp_path / "music"
    music.mkdir()
    original_iterdir = type(source).iterdir

    def unreadable_iterdir(path: Path):
        if path == music:
            raise OSError("access denied")
        return original_iterdir(path)

    monkeypatch.setattr(type(source), "iterdir", unreadable_iterdir)

    result = validate_selection(
        GuiSelection(input_dir=source, music_path=music, output_dir=tmp_path / "out")
    )

    assert result.ready is False
    assert result.status == JobStatus.IDLE
    assert f"Unable to read music folder: {music}" in result.messages
