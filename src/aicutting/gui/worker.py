from PySide6.QtCore import QObject, Signal, Slot

from aicutting.core.progress import CancellationToken, ProgressEvent
from aicutting.gui.jobs import JobFailure, JobRequest, JobSuccess, run_cut_job


class CutWorker(QObject):
    progress = Signal(object)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal()

    def __init__(self, request: JobRequest, token: CancellationToken | None = None) -> None:
        super().__init__()
        self.request = request
        self.token = token or CancellationToken()

    def cancel(self) -> None:
        self.token.cancel()

    @Slot()
    def run(self) -> None:
        def report(event: ProgressEvent) -> None:
            self.token.raise_if_cancelled()
            self.progress.emit(event)

        result = run_cut_job(self.request, progress=report)
        if isinstance(result, JobSuccess):
            self.succeeded.emit(result.result)
        elif isinstance(result, JobFailure):
            self.failed.emit(result)
        self.finished.emit()
