from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aicutting.core.progress import CancellationToken, ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest
from aicutting.gui.state import GuiSelection, JobStatus, default_output_dir, validate_selection
from aicutting.gui.widgets import PathPicker, StatusPanel
from aicutting.gui.worker import CutWorker
from aicutting.pipeline import PipelineResult


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AiCutting Studio")
        self.status = JobStatus.IDLE
        self.thread: QThread | None = None
        self.worker: CutWorker | None = None
        self.cancel_token: CancellationToken | None = None
        self.close_requested = False
        self._terminal_message: str | None = None

        self.video_picker = PathPicker("Video folder", "Choose")
        self.music_picker = PathPicker("Music", "Choose")
        self.output_picker = PathPicker("Output", "Choose")
        self.start_button = QPushButton("Start")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.status_panel = StatusPanel()
        self.result_label = QLabel("")

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel("AiCutting Studio"))
        layout.addWidget(self.video_picker)
        layout.addWidget(self.music_picker)
        layout.addWidget(self.output_picker)

        actions = QHBoxLayout()
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        layout.addWidget(self.status_panel)
        layout.addWidget(self.result_label)
        self.setCentralWidget(root)

        self.video_picker.button.clicked.connect(self.choose_video_folder)
        self.music_picker.button.clicked.connect(self.choose_music)
        self.output_picker.button.clicked.connect(self.choose_output_folder)
        self.start_button.clicked.connect(self.start_job)
        self.cancel_button.clicked.connect(self.cancel_job)

        self.video_picker.path_changed.connect(lambda _: self.refresh_ready_state())
        self.music_picker.path_changed.connect(lambda _: self.refresh_ready_state())
        self.output_picker.path_changed.connect(lambda _: self.refresh_ready_state())
        self.refresh_ready_state()

    def current_selection(self) -> GuiSelection:
        return GuiSelection(
            input_dir=self.video_picker.path(),
            music_path=self.music_picker.path(),
            output_dir=self.output_picker.path(),
        )

    def set_inputs_enabled(self, enabled: bool) -> None:
        self.video_picker.setEnabled(enabled)
        self.music_picker.setEnabled(enabled)
        self.output_picker.setEnabled(enabled)

    def is_job_active(self) -> bool:
        return self.thread is not None or self.status in {
            JobStatus.RUNNING,
            JobStatus.CANCEL_REQUESTED,
        }

    def choose_video_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose video folder")
        if selected:
            path = Path(selected)
            self.video_picker.set_path(path)
            if self.output_picker.path() is None:
                self.output_picker.set_path(default_output_dir(path))

    def choose_music(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Choose music",
            "",
            "Audio files (*.wav *.mp3 *.m4a *.aac *.flac)",
        )
        if selected:
            self.music_picker.set_path(Path(selected))

    def choose_output_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if selected:
            self.output_picker.set_path(Path(selected))

    def refresh_ready_state(self) -> None:
        if self.is_job_active():
            self.start_button.setEnabled(False)
            return

        validation = validate_selection(self.current_selection())
        self.status = validation.status
        self.start_button.setEnabled(validation.ready)
        if validation.messages:
            self.status_panel.set_status(validation.messages[0], busy=False)
        else:
            self.status_panel.set_status("Ready", busy=False)

    def start_job(self) -> None:
        if self.is_job_active():
            return

        validation = validate_selection(self.current_selection())
        if not validation.ready:
            self.refresh_ready_state()
            return

        selection = self.current_selection()
        assert selection.input_dir is not None
        assert selection.output_dir is not None
        request = JobRequest(
            input_dir=selection.input_dir,
            music_path=selection.music_path,
            output_dir=selection.output_dir,
            dry_run=selection.dry_run,
        )

        self.cancel_token = CancellationToken()
        self.thread = QThread()
        self.worker = CutWorker(request, self.cancel_token)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_worker_finished)

        self.status = JobStatus.RUNNING
        self._terminal_message = None
        self.result_label.clear()
        self.set_inputs_enabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_panel.set_status("Starting", busy=True)
        self.thread.start()

    def cancel_job(self) -> None:
        if not self.is_job_active():
            return

        self.status = JobStatus.CANCEL_REQUESTED
        self.cancel_button.setEnabled(False)
        self.status_panel.set_status("Stopping after the current step", busy=True)
        if self.cancel_token is not None:
            self.cancel_token.cancel()

    def on_progress(self, event: ProgressEvent) -> None:
        self.status_panel.set_status(event.message or event.phase.value, busy=True)
        self.status_panel.append_log(event.message or event.phase.value)

    def on_success(self, result: PipelineResult) -> None:
        self.status = JobStatus.COMPLETE
        self.status_panel.set_status("Done", busy=False)
        self.result_label.setText(f"Finished video: {result.final_video}")
        self._terminal_message = "Done"

    def on_failure(self, failure: JobFailure) -> None:
        self.result_label.clear()
        if failure.error_type == "PipelineCancelledError":
            self.status = JobStatus.IDLE
            self.status_panel.set_status("Cancelled", busy=False)
            self._terminal_message = "Cancelled"
            return

        self.status = JobStatus.FAILED
        self.status_panel.set_status(failure.message, busy=False)
        self.status_panel.append_log(f"{failure.error_type}: {failure.message}")
        self._terminal_message = failure.message

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.is_job_active():
            event.accept()
            return

        self.close_requested = True
        self.status = JobStatus.CANCEL_REQUESTED
        self.cancel_button.setEnabled(False)
        self.status_panel.set_status("Stopping before closing", busy=True)
        if self.cancel_token is not None:
            self.cancel_token.cancel()
        event.ignore()

    def on_worker_finished(self) -> None:
        close_requested = self.close_requested
        terminal_message = self._terminal_message
        was_cancelled = terminal_message == "Cancelled"

        self.thread = None
        self.worker = None
        self.cancel_token = None
        self.cancel_button.setEnabled(False)
        self.set_inputs_enabled(True)
        self.refresh_ready_state()
        if terminal_message is not None:
            self.status_panel.set_status(terminal_message, busy=False)
            self._terminal_message = None
        if was_cancelled:
            self.status = JobStatus.IDLE
        if close_requested:
            self.close_requested = False
            self.close()
