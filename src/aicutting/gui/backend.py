from pathlib import Path

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from aicutting.core.progress import CancellationToken, PipelinePhase, ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest
from aicutting.gui.state import GuiSelection, validate_selection
from aicutting.gui.worker import CutWorker
from aicutting.pipeline import PipelineResult

# The 13 pipeline phases grouped into 5 premium stages shown in the UI.
_PHASE_STAGE: dict[PipelinePhase, int] = {
    PipelinePhase.CHECKING_INPUTS: 0,
    PipelinePhase.FINDING_VIDEOS: 0,
    PipelinePhase.ANALYZING_FOOTAGE: 1,
    PipelinePhase.ANALYZING_MUSIC: 1,
    PipelinePhase.IDENTIFYING_LOCATION: 1,
    PipelinePhase.RATING_FOOTAGE: 2,
    PipelinePhase.DESIGNING_EDIT: 2,
    PipelinePhase.ASSEMBLING_CUT: 3,
    PipelinePhase.PLANNING_CUT: 3,
    PipelinePhase.BUILDING_REPORT: 3,
    PipelinePhase.EXPORTING_RESOLVE_HANDOFF: 3,
    PipelinePhase.RENDERING_FINAL_VIDEO: 4,
    PipelinePhase.DONE: 4,
}


def phase_to_stage(phase: PipelinePhase) -> int:
    return _PHASE_STAGE.get(phase, 0)


class Backend(QObject):
    """Bridge between QML and the existing CutWorker/pipeline. Owns the worker thread and exposes
    the run state as bindable properties; QML animates off the notify signals."""

    statusChanged = Signal()
    stageIndexChanged = Signal()
    liveMessageChanged = Signal()
    busyChanged = Signal()
    gradeChanged = Signal()
    resultChanged = Signal()
    chosenFolderChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "idle"
        self._folder = ""
        self._stage = -1
        self._message = ""
        self._busy = False
        self._grade = ""
        self._grade_overall = 0.0
        self._dims = {"on_beat": 0.0, "variety": 0.0, "pacing": 0.0}
        self._final = ""
        self._report = ""
        self._output = ""
        self._resolve = ""
        self._has_teaser = False
        self._has_short = False
        self._thread: QThread | None = None
        self._worker: CutWorker | None = None
        self._token: CancellationToken | None = None

    # --- properties (read-only to QML; updated from Python) ---
    def _get_status(self) -> str:
        return self._status

    status = Property(str, _get_status, notify=statusChanged)

    def _get_folder(self) -> str:
        return self._folder

    chosenFolder = Property(str, _get_folder, notify=chosenFolderChanged)

    def _get_stage(self) -> int:
        return self._stage

    stageIndex = Property(int, _get_stage, notify=stageIndexChanged)

    def _get_message(self) -> str:
        return self._message

    liveMessage = Property(str, _get_message, notify=liveMessageChanged)

    def _get_busy(self) -> bool:
        return self._busy

    busy = Property(bool, _get_busy, notify=busyChanged)

    def _get_grade(self) -> str:
        return self._grade

    grade = Property(str, _get_grade, notify=gradeChanged)

    def _get_grade_overall(self) -> float:
        return self._grade_overall

    gradeOverall = Property(float, _get_grade_overall, notify=gradeChanged)

    def _get_on_beat(self) -> float:
        return self._dims["on_beat"]

    onBeat = Property(float, _get_on_beat, notify=gradeChanged)

    def _get_variety(self) -> float:
        return self._dims["variety"]

    variety = Property(float, _get_variety, notify=gradeChanged)

    def _get_pacing(self) -> float:
        return self._dims["pacing"]

    pacing = Property(float, _get_pacing, notify=gradeChanged)

    def _get_final(self) -> str:
        return self._final

    finalVideo = Property(str, _get_final, notify=resultChanged)

    def _get_report(self) -> str:
        return self._report

    reportPath = Property(str, _get_report, notify=resultChanged)

    def _get_output(self) -> str:
        return self._output

    outputDir = Property(str, _get_output, notify=resultChanged)

    def _get_has_teaser(self) -> bool:
        return self._has_teaser

    hasTeaser = Property(bool, _get_has_teaser, notify=resultChanged)

    def _get_has_short(self) -> bool:
        return self._has_short

    hasShort = Property(bool, _get_has_short, notify=resultChanged)

    # --- slots invoked from QML ---
    @Slot(str)
    def setFolder(self, path: str) -> None:
        folder = Path(path)
        result = validate_selection(
            GuiSelection(input_dir=folder, output_dir=folder / "aicutting-out")
        )
        if not result.ready:
            self._message = result.messages[0] if result.messages else "Invalid footage folder."
            self.liveMessageChanged.emit()
            self._set_status("error")
            return
        self._folder = path
        self.chosenFolderChanged.emit()
        self._set_status("compose")

    @Slot()
    def reset(self) -> None:
        self._folder = ""
        self.chosenFolderChanged.emit()
        self._set_status("idle")

    @Slot(str, str, str, str, bool)
    def startCut(self, folder: str, music: str, style: str, aspect: str, variants: bool) -> None:
        if self._busy:
            return
        request = JobRequest(
            input_dir=Path(folder),
            music_path=Path(music) if music else None,
            output_dir=Path(folder) / "aicutting-out",
            style=style or "cinematic",
            aspect=aspect or "16:9",
            variants=variants,
        )
        self._token = CancellationToken()
        self._worker = CutWorker(request, token=self._token)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._set_status("working")
        self._set_busy(True)
        self._thread.start()

    @Slot()
    def cancel(self) -> None:
        if self._token is not None:
            self._token.cancel()

    @Slot()
    def openVideo(self) -> None:
        self._open(self._final)

    @Slot()
    def openReport(self) -> None:
        self._open(self._report)

    @Slot()
    def openFolder(self) -> None:
        self._open(self._output)

    @Slot()
    def openInResolve(self) -> None:
        self._open(self._resolve)

    @Slot(str, result=int)
    def countClips(self, folder: str) -> int:
        suffixes = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
        try:
            return sum(1 for p in Path(folder).iterdir() if p.suffix.lower() in suffixes)
        except OSError:
            return 0

    # --- worker signal handlers ---
    def _on_progress(self, event: ProgressEvent) -> None:
        self._stage = phase_to_stage(event.phase)
        self.stageIndexChanged.emit()
        self._message = event.message or event.phase.value
        self.liveMessageChanged.emit()

    def _on_succeeded(self, result: PipelineResult) -> None:
        self._grade = result.grade or ""
        self._grade_overall = result.grade_overall or 0.0
        self._dims = {**self._dims, **result.grade_dimensions}
        self._final = str(result.final_video)
        self._report = str(result.output_dir / "report.html")
        self._output = str(result.output_dir)
        self._resolve = str(result.output_dir / "resolve")
        self._has_teaser = (result.output_dir / "final-teaser.mp4").exists()
        self._has_short = (result.output_dir / "final-short.mp4").exists()
        self.gradeChanged.emit()
        self.resultChanged.emit()
        self._set_busy(False)
        self._set_status("result")

    def _on_failed(self, failure: JobFailure) -> None:
        self._message = failure.message
        self.liveMessageChanged.emit()
        self._set_busy(False)
        self._set_status("error")

    # --- helpers ---
    def _open(self, path: str) -> None:
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()
