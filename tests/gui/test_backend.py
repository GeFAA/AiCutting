
from aicutting.core.progress import PipelinePhase, ProgressEvent
from aicutting.gui.backend import Backend, phase_to_stage
from aicutting.pipeline import PipelineResult


def test_phase_to_stage_maps_the_pipeline_into_five_stages() -> None:
    assert phase_to_stage(PipelinePhase.CHECKING_INPUTS) == 0  # Ingest
    assert phase_to_stage(PipelinePhase.ANALYZING_FOOTAGE) == 1  # Watch
    assert phase_to_stage(PipelinePhase.RATING_FOOTAGE) == 2  # Direct
    assert phase_to_stage(PipelinePhase.ASSEMBLING_CUT) == 3  # Cut
    assert phase_to_stage(PipelinePhase.RENDERING_FINAL_VIDEO) == 4  # Render


def test_every_phase_maps_to_a_valid_stage() -> None:
    assert all(0 <= phase_to_stage(phase) <= 4 for phase in PipelinePhase)


def test_backend_starts_idle(qtbot) -> None:  # type: ignore[no-untyped-def]
    backend = Backend()
    assert backend.status == "idle"
    assert backend.stageIndex == -1
    assert backend.busy is False


def _folder_with_video(tmp_path):  # type: ignore[no-untyped-def]
    folder = tmp_path / "footage"
    folder.mkdir()
    (folder / "clip.mp4").write_text("", encoding="utf-8")
    return folder


def test_backend_set_folder_moves_to_compose(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    folder = _folder_with_video(tmp_path)
    backend = Backend()
    with qtbot.waitSignal(backend.statusChanged):
        backend.setFolder(str(folder))
    assert backend.status == "compose"
    assert backend.chosenFolder == str(folder)


def test_backend_rejects_a_folder_without_videos(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    empty = tmp_path / "empty"
    empty.mkdir()
    backend = Backend()
    with qtbot.waitSignal(backend.statusChanged):
        backend.setFolder(str(empty))
    assert backend.status == "error"  # no videos -> not allowed to compose


def test_backend_reset_returns_to_idle(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    backend = Backend()
    backend.setFolder(str(_folder_with_video(tmp_path)))
    with qtbot.waitSignal(backend.statusChanged):
        backend.reset()
    assert backend.status == "idle"
    assert backend.chosenFolder == ""


def test_backend_maps_progress_to_a_stage(qtbot) -> None:  # type: ignore[no-untyped-def]
    backend = Backend()
    with qtbot.waitSignal(backend.stageIndexChanged):
        backend._on_progress(ProgressEvent(PipelinePhase.RATING_FOOTAGE, message="rating 12"))
    assert backend.stageIndex == 2
    assert backend.liveMessage == "rating 12"


def test_backend_fills_grade_fields_on_success(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    backend = Backend()
    result = PipelineResult(
        analysis=tmp_path / "a.json",
        cut_plan=tmp_path / "c.json",
        timeline=tmp_path / "t.json",
        final_video=tmp_path / "final.mp4",
        output_dir=tmp_path,
        grade="A",
        grade_overall=0.93,
        grade_dimensions={"on_beat": 0.98, "variety": 1.0, "pacing": 0.82},
    )
    with qtbot.waitSignal(backend.statusChanged):
        backend._on_succeeded(result)

    assert backend.status == "result"
    assert backend.grade == "A"
    assert backend.gradeOverall == 0.93
    assert backend.onBeat == 0.98
    assert backend.busy is False
    assert backend.finalVideo.endswith("final.mp4")
