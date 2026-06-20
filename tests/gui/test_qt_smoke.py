import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("PySide6") is None,
    reason="PySide6 is not installed",
)


def _load_widgets():
    pytest.importorskip("PySide6.QtWidgets")
    from aicutting.gui.widgets import PathPicker, StatusPanel

    return PathPicker, StatusPanel


def _load_main_window():
    pytest.importorskip("PySide6.QtWidgets")
    from aicutting.core.progress import CancellationToken
    from aicutting.gui.jobs import JobFailure
    from aicutting.gui.main_window import MainWindow
    from aicutting.gui.state import JobStatus

    return CancellationToken, JobFailure, JobStatus, MainWindow


def _prepare_ready_window(window, tmp_path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "clip.mp4").write_bytes(b"fake video")
    window.video_picker.set_path(input_dir)
    window.output_picker.set_path(tmp_path / "output")


def test_path_picker_constructs(qtbot) -> None:
    PathPicker, _ = _load_widgets()
    picker = PathPicker(label="Video folder", button_text="Choose")
    qtbot.addWidget(picker)

    assert picker.path() is None
    assert picker.label_text == "Video folder"


def test_status_panel_updates_message(qtbot) -> None:
    _, StatusPanel = _load_widgets()
    panel = StatusPanel()
    qtbot.addWidget(panel)

    panel.set_status("Analyzing footage")

    assert panel.current_message == "Analyzing footage"


def test_main_window_constructs(qtbot) -> None:
    _, _, _, MainWindow = _load_main_window()
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "AiCutting Studio"
    assert window.start_button.isEnabled() is False


def test_main_window_keeps_start_disabled_while_active(qtbot, tmp_path) -> None:
    _, _, JobStatus, MainWindow = _load_main_window()
    window = MainWindow()
    qtbot.addWidget(window)
    _prepare_ready_window(window, tmp_path)

    assert window.start_button.isEnabled() is True

    window.status = JobStatus.RUNNING
    window.refresh_ready_state()

    assert window.start_button.isEnabled() is False


def test_main_window_treats_cancellation_as_non_error(qtbot, tmp_path) -> None:
    _, JobFailure, JobStatus, MainWindow = _load_main_window()
    window = MainWindow()
    qtbot.addWidget(window)
    _prepare_ready_window(window, tmp_path)
    window.result_label.setText("Finished video: stale.mp4")

    window.on_failure(
        JobFailure(
            message="Cut was cancelled by the user.",
            error_type="PipelineCancelledError",
        )
    )

    assert window.status == JobStatus.IDLE
    assert window.status_panel.current_message == "Cancelled"
    assert window.result_label.text() == ""
    assert "PipelineCancelledError" not in window.status_panel.log.toPlainText()

    window.on_worker_finished()

    assert window.status == JobStatus.IDLE
    assert window.start_button.isEnabled() is True
    assert window.status_panel.current_message == "Cancelled"


def test_main_window_close_requests_cancellation_for_active_job(qtbot) -> None:
    CancellationToken, _, JobStatus, MainWindow = _load_main_window()
    window = MainWindow()
    qtbot.addWidget(window)
    token = CancellationToken()
    window.cancel_token = token
    window.status = JobStatus.RUNNING

    class CloseEvent:
        def __init__(self) -> None:
            self.accepted = False
            self.ignored = False

        def accept(self) -> None:
            self.accepted = True

        def ignore(self) -> None:
            self.ignored = True

    event = CloseEvent()

    window.closeEvent(event)

    assert event.ignored is True
    assert event.accepted is False
    assert token.cancelled is True
    assert window.close_requested is True
    assert window.status_panel.current_message == "Stopping before closing"
