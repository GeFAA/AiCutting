from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aicutting.core.progress import ProgressEvent
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
        validation = validate_selection(self.current_selection())
        self.status = validation.status
        self.start_button.setEnabled(validation.ready)
        if validation.messages:
            self.status_panel.set_status(validation.messages[0], busy=False)
        else:
            self.status_panel.set_status("Ready", busy=False)

    def start_job(self) -> None:
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

        self.thread = QThread()
        self.worker = CutWorker(request)
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
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_panel.set_status("Starting", busy=True)
        self.thread.start()

    def cancel_job(self) -> None:
        self.status = JobStatus.CANCEL_REQUESTED
        self.cancel_button.setEnabled(False)
        self.status_panel.set_status("Stopping after the current step", busy=True)
        if self.worker is not None:
            self.worker.cancel()

    def on_progress(self, event: ProgressEvent) -> None:
        self.status_panel.set_status(event.message or event.phase.value, busy=True)
        self.status_panel.append_log(event.message or event.phase.value)

    def on_success(self, result: PipelineResult) -> None:
        self.status = JobStatus.COMPLETE
        self.status_panel.set_status("Done", busy=False)
        self.result_label.setText(f"Finished video: {result.final_video}")

    def on_failure(self, failure: JobFailure) -> None:
        self.status = JobStatus.FAILED
        self.status_panel.set_status(failure.message, busy=False)
        self.status_panel.append_log(f"{failure.error_type}: {failure.message}")

    def on_worker_finished(self) -> None:
        self.cancel_button.setEnabled(False)
        if self.status in {JobStatus.COMPLETE, JobStatus.FAILED}:
            self.start_button.setEnabled(True)
        self.thread = None
        self.worker = None
