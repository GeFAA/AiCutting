from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from aicutting.core.errors import AiCuttingError


class PipelinePhase(StrEnum):
    CHECKING_INPUTS = "checking_inputs"
    FINDING_VIDEOS = "finding_videos"
    ANALYZING_FOOTAGE = "analyzing_footage"
    ANALYZING_MUSIC = "analyzing_music"
    PLANNING_CUT = "planning_cut"
    EXPORTING_RESOLVE_HANDOFF = "exporting_resolve_handoff"
    RENDERING_FINAL_VIDEO = "rendering_final_video"
    DONE = "done"


PHASE_LABELS: dict[PipelinePhase, str] = {
    PipelinePhase.CHECKING_INPUTS: "Checking inputs",
    PipelinePhase.FINDING_VIDEOS: "Finding videos",
    PipelinePhase.ANALYZING_FOOTAGE: "Analyzing footage",
    PipelinePhase.ANALYZING_MUSIC: "Analyzing music",
    PipelinePhase.PLANNING_CUT: "Planning cut",
    PipelinePhase.EXPORTING_RESOLVE_HANDOFF: "Exporting Resolve handoff",
    PipelinePhase.RENDERING_FINAL_VIDEO: "Rendering final video",
    PipelinePhase.DONE: "Done",
}


class PipelineCancelledError(AiCuttingError):
    pass


@dataclass(frozen=True)
class ProgressEvent:
    phase: PipelinePhase
    message: str | None = None
    step: int | None = None
    total: int | None = None

    def __post_init__(self) -> None:
        if self.message is None:
            object.__setattr__(self, "message", PHASE_LABELS[self.phase])


ProgressCallback = Callable[[ProgressEvent], None]


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def raise_if_cancelled(self) -> None:
        if self._cancelled:
            raise PipelineCancelledError("Cut was cancelled by the user.")


def emit_progress(
    callback: ProgressCallback | None,
    phase: PipelinePhase,
    message: str | None = None,
    step: int | None = None,
    total: int | None = None,
) -> None:
    if callback is not None:
        callback(ProgressEvent(phase=phase, message=message, step=step, total=total))
